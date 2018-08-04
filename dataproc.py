import pandas as pd
import numpy as np
import os
import warnings
import constants as cfg
from rpy2 import robjects as robj
from rpy2.robjects import r, pandas2ri
from rpy2.robjects.packages import importr
with warnings.catch_warnings():   #filter out warnings about ggplot2 version
    warnings.simplefilter("ignore")
    import rpy2.robjects.lib.ggplot2 as ggp
# $rpy2$ here to clean up saving of plots to file
from rpy2.rinterface import RRuntimeWarning
warnings.filterwarnings("ignore", category=RRuntimeWarning)
from collections import OrderedDict
from datetime import datetime


df = pd.DataFrame()
rdf = {}
dateRange = ()
colRename = {}
colOrigTimestamp = 'Time' #default guess
dataGenList = []
plotTitle = '"May the Fourth"'

def gen_command(cmdtype, parent, gen_node, custname=False):
    if custname:
        custbool = len(custname) > 0
    else:
        custbool = False
    if cmdtype == "basic":
        node = gen_node("Basic Stats", parent, data_present, stats)
    elif cmdtype == "procdata":
        node = gen_node("Process new data", parent, None, lacedata)
    elif cmdtype == "daterange":
        node = gen_node("Set date range", parent, data_present, range_set)
    elif cmdtype == "timeplot":
        node = gen_node(("Show data over time", custname)[custbool], parent,
                        data_present, timeseries)
    elif cmdtype == "boxplot":
        node = gen_node(("Boxplots", custname)[custbool], parent, data_present,
                        boxplot)
    elif cmdtype == "ldc":
        node = gen_node(("Load Duration Curve(standard)", custname)[custbool],
                        parent, data_present, ldc)
    elif cmdtype == "correlate":
        node = gen_node(("Correlation Demo", custname)[custbool],
                        parent, data_present, correlate)
    return node

def activate_r(data=None):
    global rdf
    if not rdf:
        pandas2ri.activate()   #activate conversion for Series type
    #note: R converts , to a .  So eg: gas,CCGT becomes gas.CCGT
    if isinstance(data, pd.DataFrame) and not data.empty:
        rdf = pandas2ri.py2ri(data)
    else:
        rdf = pandas2ri.py2ri(df)

def reset():
    global df   #~todo~ add other variables necessary here
    df = pd.DataFrame()

def stats():
    if dateRange:
        activate_r( df[dateRange[0]:dateRange[1]] )
    else:
        activate_r()
    base = importr('base')
    print( base.summary(rdf) )
    # check if data needs to & has been aggregated; if not, then provide option
    if not df.agged and cfg.config['general'].get('aggregate', False):
        choice = proceed()
        aggdata()
        if dateRange:
            activate_r( df[dateRange[0]:dateRange[1]] )
        else:
            activate_r()
        base = importr('base')
        print( base.summary(rdf) )

def range_selected():
    global plotTitle
    if df.empty:
        range = "---"
    elif dateRange:
        range = "{} to {}".format(dateRange[0], dateRange[1])
        plotTitle = cfg.title(dateRange[0], dateRange[1],
                              os.path.basename(os.getcwd()))
    else:
        range = "{} to {}".format(df.index[0], df.index[-1])
        plotTitle = cfg.title(df.index[0], df.index[-1],
                              os.path.basename(os.getcwd()))
    return "date range: {}".format(range)

def range_set():
    global dateRange
    if df.empty:
        return
    if dateRange:
        start = dateRange[0]
        end = dateRange[1]
    else:
        start = df.index[0]
        end = df.index[-1]
    #~todo~ need to add a bunch of error handling, etc here
    (year, month, day) = map(int, input("...set start date > ").split("-"))
    start = df[datetime(year, month, day):].first_valid_index()
    (year, month, day) = map(int, input("...set end date > ").split("-"))
    end = df[:datetime(year, month, day)].last_valid_index()
    dateRange = (start, end)

def to_dotform(original):
    commadex = original.find(',')
    if commadex == -1:
        return original
    else:
        return original[:commadex] + '.' + original[commadex+1:]

def proceed(filename=""):
#~todo~ add more flexible options eg. autosave, or not, allow interactivity
    if len(filename) > 0:
        currentdir = datetime.now().strftime('%Y%m%d')
        if not os.path.exists(currentdir):
            print("...creating directory: " + currentdir)
            os.makedirs(currentdir)
        filebase = filename[:filename.rfind('.')]
        filetype = filename[filename.rfind('.'):]
        filelist = [f for f in os.listdir(currentdir) if os.path.isfile(
                                                  os.path.join(currentdir, f))]
        filesave = os.path.join(currentdir, filename)
        if filename not in filelist:
            print("...saving as " + filesave)
            #just let the default size be saved & ignore the runtime warning
            r.ggsave( filesave )
        else:
            filelist.remove(filename)
            existing = list(map(int, [f[len(filebase):-len(filetype)]
                                for f in filelist if f.startswith(filebase)]))
            if len(existing) == 0:
                filename = filebase + "1" + filetype
            else:
                lastindex = max(existing) + 1
                filename = filebase + str(lastindex) + filetype
            filesave = os.path.join(currentdir, filename)
            print("...saving as " + filesave)
            r.ggsave( filesave )
    return input("...continue > ")


#~todo~ ALL output should have a "#whtr" watermark
#~todo~ add methods for generation boxplots, variability measure, raw R code...
#...time plot of generation + weekday/weekend typical curve w/ range
#...simulation mod(x1.5 wind for example, or SA mix in NSW)
#...spin out simulation option as class object to enable further customisation
#also: ldc w/ price, CO₂, gen type
#also: correlation of wind generation to solar, also across states, etc
#also: export/import b/w regions... eg SA & Vic w/ price/CO₂/... data
#~todo~ allow setting of global title on all plots (via .whtr?)
#~todo~ keep focus on CLI window as plots are displayed

# +++++++++++++++++++++++
# +++ data procedures +++
# +++++++++++++++++++++++

# ggplot tweaks
def watermark():
    return r('annotate("text", label="scriptstyle(italic(\\"#whtr\\"))", '\
             'x=-Inf, y=Inf, hjust=0, vjust=1, colour="grey", parse="True")')

def ldc(nonstandard=None):
    #~todo~ account for any date range limitations here...
    #~todo~ efficiency improvement(eff-imp): allow method to re-run multiple
    #times using different flag settings on same processed data...
    #~todo~ eff-imp: pre-process data once *before* running different methods
    #~todo~ use caption option to indicate source of data
    #~todo~ colour-code ldc by time stamp eg night, morning, day, evening
    (resid, resid_colour) = ("residual", "blue")
    (adjust, adjust_colour) = ("adjusted", "red")
    singleRun = True
    singlePlot = True
    anote = False
    # ggplot tweaks
    def reshare(ymax, ymin, xmax, share, dodge=False, includehydro=False):
        span = ymax-ymin
        parapoz = 1.8   #vertical offset for renewable % share info
        if dodge:
            xoff = int(0.6*xmax)
            yoff = int(ymax - 0.05*span)
        else:
            xoff = 50
            yoff = int(ymax - 0.7*span)
        nfo = [ 'annotate("text",label="underline(\\"{}renewables\nshare\\")"'\
                ', x={}, y={}, hjust=0, vjust=0, colour="darkgreen", '\
                'lineheight=0.85, parse="True")'.format(("non-hydro\n",
                                               "")[includehydro], xoff, yoff) ]
        if not np.isnan(share[0]):
            nfo.append('annotate("text", label="{:.1%} {}", x={}, y={}, ' \
                       'hjust=0, vjust={}, colour="{}")'.format(share[0],
                                     resid, xoff, yoff, parapoz, resid_colour))
            parapoz = 2*parapoz
        if (len(share) == 2) and not np.isnan(share[1]):
            nfo.append('annotate("text", label="{:.1%} {}", x={}, y={}, ' \
                       'hjust=0, vjust={}, colour="{}")'.format(share[1],
                                   adjust, xoff, yoff, parapoz, adjust_colour))
        #return as an array of strings, because appending as r() object fails
        return nfo
#    def baseload(lpp):
#        lpp += ggp.geom_hline(yintercept=500, linetype='dashed') + \
#        r('annotate("text", label="500", x=1000, y=500, hjust=0, vjust=-0.1)')
    def slimshady(top, bottom, linecolour="royalblue", backslash=False):
    #~todo~ potential here for generalised utility ala geom_ribbon()
    #~todo~ alternate, simpler approach: join points from each line with an
    #offset... would work on forward slash
        maxpoint = top.iloc[0]
        width = len(top)
        slope = maxpoint/(0.6*width)
        if backslash:
            slope = -slope
        delta = int(maxpoint/30)
        offset = (0.4, 0.75)[backslash]
        #formulate line hatches
        #note assumption that all top & bottom lines are uniformly decreasing
        (xfrom, xto, yfrom, yto) = ([], [], [], [])
        if backslash:   #range needs to be adjusted to ensure area is covered
            iTest = -slope*width + top.iloc[-1] - offset*delta
            lineTest = top.values - [iTest + slope*x
                                     for x in range(1, width+1)] > 0
            while lineTest.any():
                iTest += delta
                lineTest = top.values - [iTest + slope*x
                                         for x in range(1, width+1)] > 0
            start = int(iTest - delta)
            increments = int((top.iloc[-1] - bottom.iloc[-1]) / delta) - 3
            iTest = start - delta*increments
            lineTest = bottom.values - [iTest + slope*x
                                        for x in range(1, width+1)] < 0
            while lineTest.any():
                iTest -= delta
                lineTest = bottom.values - [iTest + slope*x
                                            for x in range(1, width+1)] < 0
            end = int(iTest + delta)
        else:
            start = int(maxpoint-offset*delta)
            end = int(bottom.iloc[-1] - slope*width)
        #use y-axis intercept as basis for defining range
        for i in range(start, end, -delta):
            line = [i + slope*x for x in range(1, width+1)]
            overunder = top.values - line > 0
            underover = bottom.values - line > 0
            crossover = overunder[0]
            crossunder = underover[0]
            topx = ()
            bottomx = ()
            for x in range(1, width):
            #note that these are the index of the array, not the value... +1
                if overunder[x] is not crossover:
                    topx = (*topx, x)
                    crossover = overunder[x]
                if underover[x] is not crossunder:
                    bottomx = (*bottomx, x)
                    crossunder = underover[x]
            #collect endpoints
            if (len(topx) == 0):
                if backslash and (len(bottomx) == 1) and (i > bottom[0]):
                #handle special case
                    xto.append(1)
                    yto.append( line[0] )
                elif (len(bottomx) < 2):   #not multiline
                    xto.append(width)
                    yto.append( line[width-1] )
            elif (len(topx) == 1):
                xto.append(topx[0] + 1)
                yto.append( top[topx[0]] )
                if backslash and (len(bottomx) == 0) and (i > maxpoint):
                #handle special case
                    xfrom.append(width)
                    yfrom.append( line[width-1] )
                    continue
            else:   #multiple broken lines
            #assume(for now) it doesn't cross *both* lines
#                print("top line multipass", topx, "...also", bottomx)
                if (i < maxpoint):
                    xto.append(1)
                    yto.append( line[0] )
                for multipt in range(0, len(topx)-1, 2):
                    xfrom.append(topx[multipt] + 1)
                    xto.append(topx[multipt + 1] + 1)
                    yfrom.append( top[topx[multipt]] )
                    yto.append( top[topx[multipt + 1]] )
                if (len(topx) % 2):   #odd number of points
                    xfrom.append(topx[-1] + 1)
                    yfrom.append( top[topx[-1]] )
                    if (i >= maxpoint):
                        xto.append(width)
                        yto.append( line[width-1] )
                elif (i < maxpoint):   #even, but reaches sides
                    xfrom.append(width)
                    yfrom.append( line[width-1] )
                continue
            if (len(bottomx) == 0):
                xfrom.append(1)
                yfrom.append( line[0] )
            elif (len(bottomx) == 1):
                xfrom.append(bottomx[0] + 1)
                yfrom.append( bottom[bottomx[0]] )
            else:   #multiple broken lines
#                print("bottom line multipass", bottomx, "...also", topx)
                if (i > bottom[0]):
                    xto.append(1)
                    yto.append( line[0] )
                for multipt in range(0, len(bottomx)-1, 2):
                    xfrom.append(bottomx[multipt] + 1)
                    xto.append(bottomx[multipt + 1] + 1)
                    yfrom.append( bottom[bottomx[multipt]] )
                    yto.append( bottom[bottomx[multipt + 1]] )
                if (len(bottomx) % 2):   #odd number of points
                    xfrom.append(bottomx[-1] + 1)
                    yfrom.append( bottom[bottomx[-1]] )
                    if (i <= bottom[0]):
                        xto.append(width)
                        yto.append( line[width-1] )
                elif (i > bottom[0]):   #even, but reaches sides
                    xfrom.append(width)
                    yfrom.append( line[width-1] )
        #setup dataframe
        shade = {'x1': robj.IntVector(xfrom), 'x2': robj.IntVector(xto),
                 'y1': robj.IntVector(yfrom), 'y2': robj.IntVector(yto)}
        shadf = robj.DataFrame(shade)
        return ggp.geom_segment(data=shadf, mapping=ggp.aes_string(x='x1',
                            xend='x2', y='y1', yend='y2'), colour=linecolour,
                            linetype='dashed', size=0.2)
    
    aggdata()
    if nonstandard:
        print("complete this part...")
        # 'include_zero' == expand_limits(y=0) no? ylim?
        # + if multiple plots, allow keep scales the same
        # switch for calculating residual from adjusted renewables, or do both!
        # switch to group by type, or keep variants eg CCGT, OCGT etc
        # switch to indicate renewable % (non- & with hydro) on plot
        # switch to include exports on plot (& what @ charging info?)
        # allow config of residual ldc eg. solar or wind only etc.
        # ...for price info - scale_y_log10()
        # ...colour palette w/ scale_colour_brewer() or scale_colour_manual()
        # ...in aes_string use col='factor(...)'
        # ...try geom_smooth(ggp.aes_string(group='...'), method='lm')
    if singleRun:
        # sort data according to decending demand level for load duration curve
        ldf = df.sort_values(by=cfg.COL_TOTAL, ascending=False)
        count = len(ldf)
        ldf['sortorder'] = range(1, count+1)
        orderlist = ['sortorder']
        totdem = ldf[cfg.COL_TOTAL].sum()
        # build a convenience dataframe that aligns all ldcs to one variable
        ldf_wide = ldf[['sortorder', cfg.COL_PRICE, cfg.COL_TOTAL,
                        cfg.COL_EXPORT]].copy()
        #note that the datetime index remains... below could be used,
        #ldf_wide.reset_index(drop=True, inplace=True)
        #but this falls over when residual or adjusted index order included
        #~todo~ need to account for instance where data like price not present…
        # now calculate residual sans non-hydro renewables
        nonhydro = list(cfg.flatish(colRename.values(), cfg.RENEWABLES_SET))
        if cfg.COL_HYDRO in nonhydro:
            nonhydro.remove(cfg.COL_HYDRO)
        ldf['residual'] = ldf[cfg.COL_TOTAL] - ldf[nonhydro].sum(axis=1)
        ldf.sort_values(by='residual', ascending=False, inplace=True)
        ldf['residorder'] = range(1, count+1)
        orderlist.append('residorder')
        totres = ldf.loc[ldf.residual > 0, 'residual'].sum()   #sum +ve values
        #extract as numpy array, sort, then add to convenience dataframe
        #(do this to have all ldc's with declining values)
        residlist = ldf['residual'].values
        residlist[::-1].sort()   #almost certainly redundant
        ldf_wide['residual'] = residlist
        if (ldf_wide['residual'] < 0).any():
            ldf_wide['resid_positive'] = np.where(ldf_wide.residual > 0,
                                                  ldf_wide.residual, 0)
        ldf_wide['residorder'] = ldf['residorder']
        # check for any adjustment of non-hydro types
        adjldf = False
        difference = [0] * count
        for delta in filter(lambda x: x.endswith('.adjusted'), list(ldf)):
            if delta[:-9] in nonhydro:
                adjldf = True
                nonhydro.remove(delta[:-9])
                difference += df[delta].fillna(df[delta[:-9]])
            else:
                pass   #~todo~ handle residual adjustments
        if adjldf:
            if nonhydro:
                ldf['adjusted'] = ldf[cfg.COL_TOTAL] - difference \
                                                    - ldf[nonhydro].sum(axis=1)
            else:   #all renewables were adjusted
                ldf['adjusted'] = ldf[cfg.COL_TOTAL] - difference
            ldf.sort_values(by='adjusted', ascending=False, inplace=True)
            ldf['adjorder'] = range(1, count+1)
            orderlist.append('adjorder')
            totadj = ldf['adjusted'].sum()
            #complete convenience dataframe
            adjustlist = ldf['adjusted'].values
            adjustlist[::-1].sort()
            ldf_wide['adjusted'] = adjustlist
            ldf_wide['adjorder'] = ldf['adjorder']

        # now plot
        activate_r(ldf_wide)   #instead of ldf directly
#        pp = ggp.ggplot(rdf) + ggp.geom_line(ggp.aes_string(x='sortorder',
#                                            y=cfg.COL_TOTAL, colour='"total"'))
        pp = ggp.ggplot(rdf) + ggp.aes_string(x='sortorder', y=cfg.COL_TOTAL,
                                            colour='"total"') + ggp.geom_line()
        if adjldf:
#            pp += ggp.geom_line(ggp.aes_string(x='residorder', y='residual',
            pp += ggp.geom_line(ggp.aes_string(y='residual',
                              colour='"'+resid+'"'), linetype='dashed', size=1)
#            pp += ggp.geom_line(ggp.aes_string(x='adjorder', y='adjusted',
            pp += ggp.geom_line(ggp.aes_string(y='adjusted',
                                               colour='"'+adjust+'"'))
        else:
#            pp += ggp.geom_line(ggp.aes_string(x='residorder', y='residual',
            pp += ggp.geom_line(ggp.aes_string(y='residual',
                                               colour='"'+resid+'"'))
        
        #build x scale breaks & labels
        ggpxbreak = str([i*(count/4.0) for i in range(5)]).strip('[]')
        #~todo~ handle data point count for month or year periods... how?
        periodtype = "data point"
        unittypes = OrderedDict([(60/cfg.timeUnit, 'hour'),
                                 (24, 'day'), (7, 'week')])
        for x,unit in unittypes.items():
            if (count % x == 0):
                count = int(count/x)
                periodtype = unit
            else:
                break
        ggpxlabel='"0%","25%","50%","75%","100%\n({:,} {}{})"'.format(count,
                                             periodtype, ('s', '')[count == 1])
        pp += r('scale_x_continuous(breaks=c(' + ggpxbreak + '), label=c(' + \
                ggpxlabel + '))')
        
        #theme stuff
#        pp += r('theme(axis.text.x=element_text(hjust=1), ' \
#                'legend.justification=c(1,1), legend.position=c(1,1), ' \
#                'legend.title=element_blank())')
        legendoff = robj.IntVector([1,1])
        pp += ggp.theme(**{"axis.text.x": ggp.element_text(hjust=1),
                       "legend.justification": legendoff,
                       "legend.position": legendoff,
                       "legend.title": ggp.element_blank()})
        
        #legend, etc
        pp += r('scale_colour_manual(values=c("total"="black","{}"="{}","{}"' \
                '="{}"))'.format(resid, resid_colour, adjust, adjust_colour))
        pp += r('guides(colour=guide_legend(reverse=T))')
        #~todo~ provide flag to switch title & subtitle
        pp +=ggp.labs(title=plotTitle, subtitle="load duration curve",
                      x="{} minute periods".format(cfg.timeUnit),
                      y="generation ({})".format(cfg.genUnit))
        pp += watermark()
        
        ldfdata = [cfg.COL_TOTAL, 'residual']
        if adjldf:
            ldfdata.append('adjusted')
        count = len(ldf_wide)
        
        # mins, maxs & others
        anocolour = "azure4"
        if anote:
            for x in ldfdata:
            #~todo~ figure out a good way to dodge lines & anything else
                baseload = ldf_wide[x].iloc[-1]
                pp += ggp.geom_hline(yintercept=baseload, linetype='dashed')
                pp += r('annotate("text", label="{:,.2f} {}", x={}, y={}, ' \
                        'hjust=0, vjust=-0.2)'.format(baseload, cfg.genUnit,
                                                      int(count/3), baseload))
            if adjldf and (ldf_wide['adjusted'].iloc[0] !=
                                                 ldf_wide['residual'].iloc[0]):
                print("warning: residual peak not the same as for adjusted...")
            peak = ldf_wide[cfg.COL_TOTAL].iloc[0]
            pp += ggp.geom_segment(ggp.aes_string(x=0, xend=int(count/8),
                               y=peak, yend=peak), linetype='dotted', size=0.3)
            pp += r('annotate("text", label="{:,.2f} {}", x={}, y={}, ' \
                    'hjust=-0.1, vjust=0.5)'.format(peak, cfg.genUnit,
                                                    int(count/8), peak))
            peaketto = ldf_wide['residual'].iloc[0]
            pp += ggp.geom_segment(ggp.aes_string(x=0, xend=int(count/8),
                       y=peaketto, yend=peaketto), linetype='dotted', size=0.3)
            pp += ggp.geom_segment(ggp.aes_string(x=int(count/9),
                   xend=int(count/9), y=peak, yend=peaketto), linetype='solid',
                   colour=anocolour, size=0.3)
            pp += ggp.geom_point(ggp.aes_string(x=int(count/9), y=peak),
                                                colour=anocolour)
            pp += ggp.geom_point(ggp.aes_string(x=int(count/9), y=peaketto),
                                                colour=anocolour)
            #~todo~ find out how to do arrows via rpy2
            pp += r('annotate("text", label="Δ = {:,.2f} {}", x={}, y={}, ' \
                    'hjust=-0.05, vjust=3, colour="{}")'.format(peak-peaketto,
                                   cfg.genUnit, int(count/9), peak, anocolour))
            fivecent = int(0.05*count)
            pp += ggp.geom_segment(ggp.aes_string(x=fivecent, xend=fivecent,
                            y=0, yend=ldf_wide[cfg.COL_TOTAL].iloc[fivecent]),
                            linetype='dotted', size=0.3)
            pp += r('annotate("text", label="5%", x={}, y=0, hjust=-0.1, ' \
                    'vjust=0, colour="{}")'.format(fivecent, anocolour))
            curvatures = [-0.1, -0.2, 0.2]
            xoffset = [7, 3, 4]
            yoff = int(peak/100)
            yoffset = [2*yoff, 4*yoff, -3*yoff]
            xtra = ["", "", "(adjusted)"]
            curindex = 0
            for x in ldfdata:
                ygen = ldf_wide[x].iloc[fivecent]
                pp += ggp.geom_point(ggp.aes_string(x=fivecent, y=ygen),
                                     colour=anocolour)
                pp += r('geom_curve(aes(x={}, y={}, xend={}, yend={}), ' \
                        'curvature={}, colour="{}")'.format(fivecent, ygen,
                        fivecent*xoffset[curindex], ygen+yoffset[curindex],
                        curvatures[curindex], anocolour))
                pp += r('annotate("text", label="{:,.2f} {}{}", x={}, y={}, ' \
                        'hjust=0, vjust=0.5, colour="{}")'.format(ygen,
                        cfg.genUnit, xtra[curindex], fivecent*xoffset[curindex],
                        ygen+yoffset[curindex], anocolour))
                curindex += 1
        # renewables share info
        for x in reshare(ldf_wide[ldfdata].max(axis=0).max(),
                         ldf_wide[ldfdata].min(axis=0).min(), count,
                         [(totdem-totres)/totdem, (totdem-totadj)/totdem],
                         dodge=False, includehydro=False):
            pp += r(x)
        #~todo~ alternate shading where solar & wind (& hydro) contribution
        #fills the area...! yes, do this ASAP
        if adjldf and cfg.config['general'].get('slimshade', True):
            pp += slimshady(ldf_wide[cfg.COL_TOTAL], ldf_wide[('residual',
                          'resid_positive')[(ldf_wide['residual'] < 0).any()]])
            pp += slimshady(ldf_wide[cfg.COL_TOTAL], ldf_wide['adjusted'],
                            'tomato', True)
        else:
#            ldf_wide['resid_positive'] = np.where(ldf_wide.residual > 0, ldf_wide.residual, 0)
            pp += ggp.geom_ribbon(ggp.aes_string(x='sortorder',
         ymin=('residual', 'resid_positive')[(ldf_wide['residual'] < 0).any()],
         ymax=cfg.COL_TOTAL), alpha=0.4, fill='deepskyblue', linetype=0,
         show_legend=False)
            if adjldf:
                pp += ggp.geom_ribbon(ggp.aes_string(x='sortorder',
                               ymin='adjusted', ymax=cfg.COL_TOTAL), alpha=0.4,
                               fill="tomato", linetype=0, show_legend=False)
#need to investigate the use of annotation_custom(), but how to access grobTree
#& textGrob? ...does exist in rpy2.robjects.lib.grid.Grob
        pp.plot()
        
        #clipping override
#need to hook into pp somehow first, but apparently use of this approach will
#remove the ability to use ggsave(). also, could use the new clip="off" option
#in coord_cartesian (but only available in latest version)
#        r('gt <- ggplot_gtable(ggplot_build(pp))')
#        r('gt$layout$clip[gt$layout$name == "panel"] <- "off"')
#        r('grid.draw(gt)')

        choice = proceed()
    
#    ldf['hack'] = (ldf[cfg.COL_PRICE] + 30) * 7
#    pp = ggp.ggplot(rdf) + ggp.aes_string(x='sortorder', y=cfg.COL_TOTAL) + \
#         ggp.geom_line() + \
#         ggp.geom_point(ggp.aes_string(y='hack')) + \
#         r('scale_y_continuous(sec.axis=sec_axis(~./7-30, name="price ($/MWh)"), limits=c(0,2000))')

#    pp = ggp.ggplot(rdf) + ggp.aes_string(x='sortorder', y='hack') + \
#         ggp.geom_point() + ggp.geom_smooth(method='lm') + \
#         ggp.geom_line(ggp.aes_string(y=cfg.COL_TOTAL)) + \
#         r('scale_y_continuous(sec.axis=sec_axis(~./7-30, name="{} ({})"), limits=c(0,2000))'.format("price", cfg.priceUnit))
#    pp = ggp.ggplot(rdf) + ggp.aes_string(x='adjorder', y='hack') + \
#         ggp.geom_point() + ggp.geom_smooth(method='lm') + \
#         ggp.geom_line(ggp.aes_string(y='adjusted')) + \
#         r('scale_y_continuous(sec.axis=sec_axis(~./7-30, name="{} ({})"), limits=c(0,2000))'.format("price", cfg.priceUnit))

        #~todo~ should drop temperature & ...
        ldf.drop(labels=cfg.LIMIT_LIST, axis=1, inplace=True, errors='ignore')
    
        ldf.drop(labels=['price', cfg.COL_TOTAL, 'residual', 'adjusted', 'exports', 'solar,rooftop', 'wind', 'wind.adjusted'], axis=1, inplace=True, errors='ignore')
    
        # convert ldf to long format for more interesting plots...
        ldf_long = pd.melt(ldf, id_vars=orderlist, var_name='type', value_name='generation')
        activate_r(ldf_long)
        pp = ggp.ggplot(rdf) + ggp.aes_string(x='adjorder', y='generation', fill='type') + ggp.geom_area()
        
        #legend, etc
        pp += ggp.theme(**{"axis.text.x": ggp.element_text(hjust=1),
                       "legend.position": "bottom",
                       "legend.title": ggp.element_blank()})
        
        #~todo~ smooth out the curves as an option -> investigate streamgraph
        pp += r('scale_fill_manual("type", '\
        'values=c("red","orange","blue","green","yellow","purple"), '\
#        'breaks=c("'+cfg.COL_BATT_DIS+'","'+cfg.COL_DIESEL+'","'+cfg.COL_GAS_CCGT+'","'+cfg.COL_GAS_OCGT+'","'+cfg.COL_GAS_STEAM+'","'+cfg.COL_IMPORT+'"))')
        'labels=expression("gas"~italic("(CCGT)"),"two","three","four","five","six"))')
        #values=c("total"="black","{}"="{}","{}"="{}")
        #labels=expression(italic("(one)"),"two","three","four","five","six")
        #"scriptstyle(italic(\\"#whtr\\"))"
        
        pp.plot()
#    print(ldf_long)

def correlate(nonstandard=None):
    aggdata()
    corr_base = 'wind'
    corr_dep = 'imports'
    params_other = []
    loc_list = []
    plotType = 'basic'
    plotIndex = 0
    dotplot = True
    plotSubTitle = 'correlation plot'
    if nonstandard:
        corr_base = nonstandard['base']
        params = [corr_base, cfg.COL_TOTAL]
        if 'nonlocal' in nonstandard:
            #assume just the one type of plot required
            plotType = list(nonstandard['style'].split("|"))[0]
            #load in the non-local information
            loc_list = list(nonstandard['nonlocal'].split("|"))
            params_other = list(nonstandard['dependent'].split("|"))
        else:
            corr_deplist = list(nonstandard['dependent'].split("|"))
            plot_list = list(nonstandard['style'].split("|"))
            if (len(plot_list) == 1) or (len(corr_deplist) > 1):
                plotType = plot_list[0]
            params.extend( corr_deplist )
            #~todo~ really should check no duplicates exist, & all sorts of
            #other error checking
        if 'dotplot' in nonstandard and nonstandard['dotplot'] == "off":
            dotplot = False
    else:
        params = [corr_base, corr_dep, cfg.COL_TOTAL]
    #~todo~ in addition to multiple plots wrt to a single variable, could do
    #scatterplot matrices: 3 or more variables all compared to each other
    #~todo~ plot data (colour?) wrt 3rd variable eg total demand (or price)
    #~todo~ need to sanity check these variables are actually in dataset
    #~todo~ add ability to handle adjusted data
    
    #extract all required data from df within defined date range limit
    if dateRange:
        correlf = df[dateRange[0]:dateRange[1]][params]
    else:
        correlf = df[params]
    #also retrieve relevant data from different directory if specified
    if params_other:   #load data, then add to correlf
        if len(loc_list) == 1:
            nonlocdf = loaddata(loc_list[0], altdf=True)
            print(nonlocdf.shortname)
            #~todo~ handle case if the shortname is null
            for x in params_other:
                newname = x + '_' + nonlocdf.shortname
                if dateRange:
                #~todo~ check for & deal with data that doesn't match range
                    correlf[newname] = df[dateRange[0]:dateRange[1]][x]
                else:
                    correlf[newname] = df[x]
            corr_deplist = [x + '_' + nonlocdf.shortname for x in params_other]
        else:
            corr_deplist = []
            for locale in loc_list:
                nonlocdf = loaddata(loc_list[0], altdf=True)
                newname = params_other[0] + '_' + nonlocdf.shortname
                if dateRange:
                    correlf[newname] = \
                                 df[dateRange[0]:dateRange[1]][params_other[0]]
                else:
                    correlf[newname] = df[params_other[0]]
                corr_deplist.append(newname)
    doData = True
    # now plot
    activate_r(correlf)
    commonTheme = [ggp.theme(**{"legend.justification": robj.FloatVector([1,0.5]),
                                "legend.position": robj.FloatVector([1,0.5])}),
#                   ggp.scale_y_continuous(label='comma'),
                   watermark()]
    corrmax = correlf[corr_base].max()
    corrmin = correlf[corr_base].min()
    newrange = ggp.xlim((0, corrmin)[corrmin < 0],
                        corrmax + (corrmax - corrmin)*0.2)
#    newrange = ggp.scale_x_continuous(label='comma', limits=robj.IntVector([(0, corrmin)[corrmin < 0], corrmax + (corrmax - corrmin)*0.2]) )
#~todo~ this makes ggplot unhappy, find a fix
    while doData:
        if nonstandard:
            if len(corr_deplist) > plotIndex:
                corr_dep = corr_deplist[plotIndex]
            elif len(plot_list) > plotIndex:
                plotType = plot_list[plotIndex]
            else:
                break
            #also track if dependant variable is nonlocal
            if len(loc_list) > plotIndex:
                plotSubTitle = 'correlation plot: {}({}) vs {}({})'.format(
                    cfg.nicetype(corr_base), os.getcwd(),
                    cfg.nicetype(corr_dep[:corr_dep.rfind('_')]),
                    loc_list[plotIndex])
            elif len(loc_list) == 1:
                plotSubTitle = 'correlation plot: {}({}) vs {}({})'.format(
                    cfg.nicetype(corr_base), os.getcwd(),
                    cfg.nicetype(corr_dep[:corr_dep.rfind('_')]), loc_list[0])
            plotIndex += 1
        else:
            doData = False
        #make sure to use R style columns
        corr_base = to_dotform(corr_base)
        corr_dep = to_dotform(corr_dep)
        colourDen = "Density"
        if plotType == 'basic':
            pp = ggp.ggplot(rdf) + ggp.aes_string(x=corr_base, y=corr_dep)
            pp += ggp.geom_point(alpha=.3, size=.5)
#            pp += ggp.scale_x_continuous(label=comma)
        elif plotType == 'contour':
            pp = ggp.ggplot(rdf) + ggp.aes_string(x=corr_base, y=corr_dep)
            if dotplot:
                pp += ggp.geom_point(alpha=.3, size=.5)
            pp += ggp.geom_density2d(ggp.aes_string(colour='..level..'))
            pp += ggp.scale_colour_gradient(low='green', high='red')
            pp += newrange
        elif plotType == 'shade':
            pp = ggp.ggplot(rdf) + ggp.aes_string(x=corr_base, y=corr_dep)
            pp += ggp.stat_density2d(ggp.aes_string(fill='..level..',
                                            alpha='..level..'), geom='polygon')
            pp += ggp.scale_fill_continuous(low='green', high='red')
            pp += ggp.guides(alpha='none')
            if dotplot:
                pp += ggp.geom_point(alpha=.3, size=.5)
            pp += newrange
        elif plotType == 'third':
        #~todo~ could add an option that only shows dots
            colourDen = "Demand\n({})".format(cfg.genUnit)
            pp = ggp.ggplot(rdf) + ggp.aes_string(x=corr_base, y=corr_dep,
                                                  colour=cfg.COL_TOTAL)
            pp += newrange
            pp += ggp.stat_density2d(ggp.aes_string(fill='..level..',
                                            alpha='..level..'), geom='polygon')
            pp += ggp.scale_fill_continuous(low='green', high='red')
            pp += ggp.guides(alpha='none')
#            pp += ggp.geom_point()
            pp += ggp.geom_point(ggp.aes_string(alpha=cfg.COL_TOTAL), size=.8)
            #~todo~ don't know why above works, it just does...
            rain = robj.StrVector(["red","yellow","green","lightblue","darkblue"])
            pp += ggp.scale_colour_gradientn(colours=rain)
        else:
            continue
        pp += ggp.labs(title=plotTitle, subtitle=plotSubTitle,
                       y="{} ({})".format(cfg.nicetype(corr_dep), cfg.genUnit),
                       x="{} ({})".format(cfg.nicetype(corr_base),cfg.genUnit),
                       colour=colourDen, fill='Density')
        #~todo~ format variant types properly
        for add in commonTheme:
            pp += add
        pp.plot()
        choice = proceed("correlation.png")

def boxplot(nonstandard=None):
#~todo~ put in better control over the order in which boxplots are shown
    params = df.columns.get_values().tolist()   #~todo~ or just list(df)
    #remove any adjustment data
    params = [x for x in params if not x.endswith('adjusted')]
    #remove unnecessary data like price & temperature
    if cfg.COL_PRICE in params:
        params.remove(cfg.COL_PRICE)
    if cfg.COL_TEMP in params:
        params.remove(cfg.COL_TEMP)
    #remove total as well, but #~todo~ could set flag to keep it
    if cfg.COL_TOTAL in params:
        params.remove(cfg.COL_TOTAL)
    if nonstandard:   #for selected or customised data
        if 'mods' in nonstandard:
            if 'showmin' in list(nonstandard['mods'].split("|")):
                addMin = True
        pass
    else:
        addMin = False
#~todo~ make use of addMin flag to indicate minimum
#use below or make use of stat_summary by filtering just minimum data...
#pp += r('annotate("text", label="Δ = {:,.2f} {}", x={}, y={}, ' \
#                    'hjust=-0.05, vjust=3, colour="{}")'.format(peak-peaketto,
#                                   cfg.genUnit, int(count/9), peak, "azure4"))
    if dateRange:
        boxdf = pd.melt(df[dateRange[0]:dateRange[1]][params], var_name='type',
                        value_name='generation')
    else:
        boxdf = pd.melt(df[params], var_name='type', value_name='generation')
    activate_r(boxdf)
    commonTheme = [ggp.labs(title=plotTitle, subtitle="boxplots",
                            y="generation ({})".format(cfg.genUnit)),
                   ggp.theme(**{"axis.title.x": ggp.element_blank(),
                                "legend.position": "none"}),
                   watermark()]
    pp = ggp.ggplot(rdf) + ggp.aes_string(x='type', y='generation',
                                          colour='type')
    pp += ggp.geom_boxplot(notch=True)
    #~todo~ note that reorder below loses the wind type… fix this, then use it
#    reorder = list(cfg.flatish(params))
    relabel = [cfg.nicetype(x, template='nl') for x in params]
    pp += ggp.scale_x_discrete(limit=robj.StrVector(params),
                               label=robj.StrVector(relabel))
    palette = [cfg.colourPalette[x] for x in params]
    pp += ggp.scale_colour_manual(limit=robj.StrVector(params),
                                  values=robj.StrVector(palette))
    for add in commonTheme:
            pp += add
    pp.plot()
    choice = proceed("boxplot.png")

#~todo~ maybe turn this into a callable method to provide a plot of some kind?
def variability():
    pass   #return gen types in order, either grouped or individually

def timeseries(nonstandard=None):
#~todo~ improve the granularity of the time axis
#~todo~ make plot width bigger, and configurable
#~todo~ storage charging data is appearing below the axis (along with imports)
#need a better approach to this
    params = list(df)
    #remove unnecessary data like price & temperature
    if cfg.COL_PRICE in params:
        params.remove(cfg.COL_PRICE)
    if cfg.COL_TEMP in params:
        params.remove(cfg.COL_TEMP)
    #remove total as well, but #~todo~ could set flag to keep it
    if cfg.COL_TOTAL in params:
        params.remove(cfg.COL_TOTAL)
    if nonstandard:
        pass
    #make a copy of the original data
    if dateRange:
        timedf = df[dateRange[0]:dateRange[1]][params].copy()
    else:
        timedf = df[params].copy()
    #consolidate adjusted data
    adjust = [x for x in params if x.endswith('adjusted')]
    for x in adjust:
        timedf[x[:-9]] = timedf[x].fillna(timedf[x[:-9]])
    timedf.drop(labels=adjust, axis=1, inplace=True, errors='ignore')
    #de-index the time data
    timedf.reset_index(inplace=True)
    #generate wide format
    timedf_long = pd.melt(timedf, id_vars=[cfg.COL_TIMESTAMP], var_name='type',
                                           value_name='generation')
    #use this hack for now to establish the stack order for the plot
    #~todo~ come back & implement in a *better* way
    reorder = list(cfg.flatish(params))
    reorder.insert(-3, cfg.TYPE_WIND)   #hack this back in
    neworder = dict((tup[1], str(tup[0]))
                                 for tup in list(enumerate(reversed(reorder))))
    timedf_long['atype'] = [neworder[x]+x for x in timedf_long['type']]
    activate_r(timedf_long)
    commonTheme = [ggp.labs(title=plotTitle,
                            y="generation ({})".format(cfg.genUnit)),
                   ggp.theme(**{"axis.title.x": ggp.element_blank(),
                                "legend.position": "bottom",
                                "legend.title": ggp.element_blank()})]
    pp = ggp.ggplot(rdf) + ggp.aes_string(x=cfg.COL_TIMESTAMP, y='generation',
                                          fill='atype') + ggp.geom_area()
    palette = [cfg.colourPalette[x] for x in reorder]
    linkette = [neworder[x]+x for x in reorder]
    #~todo~ the colour scheme is aweful, make a better one
    pp += ggp.scale_fill_manual(limit=robj.StrVector(linkette),
                values=robj.StrVector(palette), labels=robj.StrVector(reorder))
    for add in commonTheme:
            pp += add
#    pp += watermark()   ...no, "time_trans works with objects of class POSIXct only"
    #~todo~ find a fix for this
    
    pp.plot()
    choice = proceed("time.png")

# +++++++++++++++++++++++++++
# +++ active status tests +++
# +++++++++++++++++++++++++++

def data_present():
    return not df.empty


# +++++++++++++++++++++
# +++ data sourcing +++
# +++++++++++++++++++++
#~todo~ add ability that can handle new energy type introduced as data evolves

def load_csv(datasource):
    global colRename, colOrigTimestamp, dataGenList
    print("...reading data from", datasource)
    if not colRename:   #setup column name translation
        print("...setting data parameters")
        colRename = dict(cfg.config['data.columns'])
        # also extract column name for timestamp in source data file
        colOrigTimestamp = next((raw for raw, new in colRename.items()
                                 if new == cfg.COL_TIMESTAMP), None)
        del colRename[colOrigTimestamp]
    if not dataGenList:
        dataGenList = list(cfg.flatish( colRename.values() ))
    # read in the data
    if cfg.config['general'].get('smartparse', False):
        dateformat = cfg.config['general'].get('dateformat', cfg.dateFormat)
        dateparser = lambda x: pd.datetime.strptime(x, dateformat)
        tdf = pd.read_csv(datasource, sep=',', parse_dates=[colOrigTimestamp],
                          date_parser=dateparser, index_col=[colOrigTimestamp])
    else:
        tdf = pd.read_csv(datasource, sep=',', parse_dates=[colOrigTimestamp],
                          index_col=[colOrigTimestamp])
    #~todo~ for data that has timezone offset -> reset to local time
    # relabel columns
    tdf.index.names = [cfg.COL_TIMESTAMP]
    tdf.rename(columns=colRename, inplace=True)
    # remove & double-check empty data columns
    discard = [x for x in list(tdf) if x not in colRename.values()]
    for check in discard:
        if (tdf[check] != 0).any():
            print("...non-zero value in", check)
    #~todo~ test that data is either always -ve or +ve
    tdf.drop(discard, axis=1, inplace=True)
    # calculate totals, if necessary (which is effectively the demand curve)
    if cfg.COL_TOTAL not in list(tdf):
        tdf[cfg.COL_TOTAL] = tdf[dataGenList].sum(axis=1)
        #note: this assumes data like exports is already negative...

    # handle data customisations
    #~todo~ provide ability to re-calculate custom values on full dataset...
    #...should it prove necessary
    # current hack for the AEMO S_WIND_1200_AUTO constraint follows...
    #note behaviour on Friday 8 June 2018 in South Australia !!!
    #~todo~ need to deal with that properly & allow pro-rata adjustments
    adjustor = cfg.config['data.customised'].get(cfg.COL_EXPORT, "")
    if adjustor:   #expected to be 'wind'
        if (abs(tdf[cfg.COL_EXPORT]) > tdf[adjustor]).any():
            print("! instance of {} generation less than that exported...".
                  format(adjustor))
        else:
            tdf[adjustor + '.adjusted'] = tdf.apply(
                          lambda x: x[adjustor] + x[cfg.COL_EXPORT]
                          if (x[cfg.COL_EXPORT] != 0) else np.nan, axis=1)
    # or tdf[adjustor + '.adjusted'] = tdf[?].where(tdf[cfg.COL_EXPORT] != 0, np.nan)
    #alternate approach would be to pro-rata reduction in all generation for
    #export amount

    return tdf

def loaddata(datasource, altdf=False, readjust=False):
    if altdf:
        #likely not to be local datasource, so load relevant configuration file
        print(os.getcwd())
        cfgsource = '../{}/.whtr'.format(datasource)
        print(cfgsource)
        currentcfg = cfg.read_config( cfgsource )
        datasource = '../{}/{}'.format(datasource,
                               currentcfg['general'].get('dbname', "whtr.csv"))
        print(datasource)
    else:
        global df
        currentcfg = cfg.config
    df = pd.read_csv(datasource, sep=';', parse_dates=[cfg.COL_TIMESTAMP],
                     index_col=[cfg.COL_TIMESTAMP])
    df.agged = False
    if altdf:
        df.shortname = currentcfg['general'].get('shortname')
    #handle aggregation
    aggs = [currentcfg['general'].get('aggregate', "")]
    if aggs and altdf:
        #~todo~ check that there isn't conflict eg. renewables & wind both in
        #list, leading to confusion
        for newcol in aggs:
            composition = list(cfg.flatish(dataGenList,
                                           cfg.GROUPINGS.get(newcol)))
            df[newcol] = df[composition].sum(axis=1)
            df.drop(labels=composition, axis=1, inplace=True, errors='ignore')
            #~todo~ any relevant 'adjusted' data is now orphaned
        df.agged = True
    if readjust:
    #~todo~ if necessary to recalc adjustment values, implement here
        pass
    return (None, df)[altdf]

def aggdata():
    if df.agged:
        pass
    else:
        aggs = [cfg.config['general'].get('aggregate', "")]
        #~todo~ parts of the following code are untested...
        if aggs:
            for newcol in aggs:
                comp = list(cfg.flatish(dataGenList,cfg.GROUPINGS.get(newcol)))
                if len(comp) == 0:
                    continue
                df[newcol] = df[comp].sum(axis=1)
                df.drop(labels=comp, axis=1, inplace=True, errors='ignore')
                #now do similar for any adjusted data
                if (len(comp) == 1) and (comp[0] + '.adjusted' in df):
                    df.rename(columns={comp[0] + '.adjusted':
                                           newcol + '.adjusted'}, inplace=True)
                else:
                    #do it this way in order to handle NaNs
                    oldata = filter(lambda x: x.endswith('.adjusted') and
                                              x[:-9] in comp, list(df))
#                    print(oldata)
                    df[newcol + '.adjusted'] = df[oldata].sum(axis=1)
                    df.drop(oldata, axis=1, inplace=True, errors='ignore')
        df.agged = True

def lacedata(datalist):
    global df
    if len(datalist) == 0:
        print(" * no data to process *")
    currentFiles = list(cfg.config['data.processed'].get('files', '').split(","))
    if not df.empty:
        df.reset_index(inplace=True)
    for dfile in datalist[:]:
        #~todo~ maybe pre-sort according to date range?
        #~todo~ also need to double check time period constant ie. 5 minutes
        #~todo~ investigate DatetimeIndex class
        tdf = load_csv(dfile)
        #and remove datafile from the list
        #~todo~ node.execute() will still fail, so fix that...
        currentFiles.append(dfile)
        datalist.remove(dfile)
        #~todo~ but add to .whtr list
        tdf.reset_index(inplace=True)   #make it easier to merge
        if df.empty:
            df = tdf
        else:
            #join tdf to df
            #~todo~ consider placing tdf`s into a list & appending once
            df.append(tdf, ignore_index=True)
            #remove (identical) duplicate rows
            dupcount = df.duplicated().sum()
            #~todo~ eff-imp: could retain series, rather than re-run check here
            if dupcount:
                print("...removing {} duplicate rows".format(dupcount))
                df.drop_duplicates(inplace=True)
                #double check & filter for duplicated timestamps
                dupcount = df.duplicated(cfg.COL_TIMESTAMP).sum()
                if dupcount:
                    print("...{} rows with same timestamp".format(dupcount))
                    df.drop_duplicates(cfg.COL_TIMESTAMP, inplace=True)
    df.set_index(cfg.COL_TIMESTAMP, inplace=True)
    df.agged = False
    # finally, write to disk
    df.to_csv("whtr.csv", sep=';')   #"revenge is mine"
    #~todo~ use custom name from .whtr
    #       use cfg['general'].get('dbname', "whtr.csv")
    #~todo~ run sanity checks on data eg. 5 minute intervals consistent
    #~todo~ store record of processed data in .whtr
    cfg.config.set('data.processed', 'files', ','.join(map(str, currentFiles)))
    cfgfile = open(".whtr", 'w')
    cfg.config.write(cfgfile)
    cfgfile.close()
    #~todo~ make sure backup is kept as well
    # then aggregate
    aggdata()


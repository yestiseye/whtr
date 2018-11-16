import pandas as pd
import numpy as np
import os
import re
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
dataFill = []
backFill = False
plotTitle = '"May the Fourth"'
filterList = []
fillList = []

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
    elif cmdtype == "boxplot":
        node = gen_node(("Boxplots", custname)[custbool], parent, data_present,
                        boxplot)
    elif cmdtype == "correlate":
        node = gen_node(("Correlation Demo", custname)[custbool], parent,
                        data_present, correlate)
    elif cmdtype == "ldc":
        node = gen_node(("Load Duration Curve(standard)", custname)[custbool],
                        parent, data_present, ldc)
    elif cmdtype == "timeplot":
        node = gen_node(("Show data over time", custname)[custbool], parent,
                        data_present, timeseries)
    elif cmdtype == "cohtoo":
        node = gen_node(("CO₂ intensity over time", custname)[custbool],
                        parent, data_present, co2intensity)
    elif cmdtype == "trend":
        node = gen_node(("Trend data", custname)[custbool], parent,
                        data_present, co2intensity)
    elif cmdtype == "sim":
        node = gen_node(("Sim Demo", custname)[custbool],
                        parent, data_present, simulation)
    return node


# +++++++++++++++++
# +++ utilities +++
# +++++++++++++++++

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
    global df, dateRange, colRename, dataGenList
    df = pd.DataFrame()
    dateRange = ()
    colRename = {}
    dataGenList = []
    print("-clearing parameters-")

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
    (year, month, day) = map(int, input("...set end date(inclusive) > ").
                                                                    split("-"))
    end = df[:'{}-{}-{} 23:59:59'.format(year, month, day)].last_valid_index()
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


#~todo~ add methods for generation boxplots, variability measure, raw R code...
#...time plot of generation + weekday/weekend typical curve w/ range
#...energy mix trend data eg. quarterly delta from previous year(s)
#...simulation mod(x1.5 wind for example, or SA mix in NSW)
#...spin out simulation option as class object to enable further customisation
#also: ldc w/ price, CO₂, gen type
#also: correlation of wind generation to solar, also across states, etc
#also: export/import b/w regions... eg SA & Vic w/ price/CO₂/... data
#~todo~ basic assumption that export & import are never non-zero simultaneously
#...requires a re-write to be able to handle this
#~todo~ keep focus on CLI window as plots are displayed
#~todo~ when dealing with combination of different datasets, make sure
#timestamps are aligned + add functionality to handle this eg NEM w/ WA
#~todo~ functionality to allow customised 'skins' global/specific -> hive off
#to a graphics.py library?
#~todo~ add functionality to call procedure 'on the fly' i.e. type 'ldc' at cli

# +++++++++++++++++++++++
# +++ data procedures +++
# +++++++++++++++++++++++

# ggplot tweaks
def watermark(timeaxis=""):
    return r('annotate("text", label="scriptstyle(italic(\\"#whtr\\"))", '\
             'x={}, y=Inf, hjust=0, vjust=1, colour="grey", ' \
             'parse="True")'.format(('-Inf', 'as.POSIXct(-Inf, origin="' + \
             timeaxis + '")')[len(timeaxis) != 0]))

# other tweaks
def scalenquant(amount):
    scaleUnits = ['kW', 'MW', 'GW', 'TW', 'PW']
    scale = scaleUnits.index( cfg.genUnit )
    #find sensible unit for display
    while amount > 10000:
        scale += 1
        amount = amount / 1000
    return (amount, scaleUnits[scale])

def pairwise(iterable):
    "s -> (s0,s1), (s2,s3), (s4,s5), ..."
    a = iter(iterable)
    return zip(a, a)


def ldc(nonstandard=None):
    #~todo~ efficiency improvement(eff-imp): allow method to re-run multiple
    #times using different flag settings on same processed data...
    #~todo~ eff-imp: pre-process data once *before* running different methods
    #~todo~ use caption option to indicate source of data
    #~todo~ colour-code ldc by time stamp eg night, morning, day, evening
    (resid, resid_colour) = ("residual", "blue")
    (adjust, adjust_colour) = ("adjusted", "red")
    doPlot = True
    baseData = True
    detailData = False
    modedData = False
    anote = False
    anotes = ['baseload', 'peak', 'delta', 'percent5']
    includeHydro = False
    onlyraw = False
    showshare = True
    showquantity = False
    showexports = False
    shading = True
    plotCusTitle = ""

    #--------------
    # ggplot tweaks
    #--------------
    def reshare(ymax, ymin, xmax, share, hydro=False, dodge=False):
        span = ymax-ymin
        parapoz = 1.8   #vertical offset for renewable % share info
        if dodge:
            xoff = int(0.6*xmax)
            yoff = int(ymax - 0.15*span)
        else:
            xoff = 50
            yoff = int(ymax - 0.7*span)
        nfo = [ 'annotate("text",label="underline(\\"{}renewables\nshare\\")"'\
                ', x={}, y={}, hjust=0, vjust=0, colour="darkgreen", '\
                'lineheight=0.85, parse="True")'.format(("non-hydro\n",
                                                    "\n")[hydro], xoff, yoff) ]
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
#            if backslash:
#                print(topx, bottomx)
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
            # !!! but then it does... :-( see <quick patch> below
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
                        # <quick patch #2 -starts->
                        if (len(bottomx) == 1):
                            xto.append(bottomx[0] + 1)
                            yto.append( bottom[bottomx[0]] )
                        else:
                        # <quick patch #2 -ends->
                            xto.append(width)
                            yto.append( line[width-1] )
                elif (i < maxpoint):   #even, but reaches sides
                    # <quick patch -starts->
                    if (len(bottomx) == 1):
                        xfrom.append(bottomx[0] + 1)
                        yfrom.append( bottom[bottomx[0]] )
                    else:
                    # <quick patch -ends->
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
                if (i > bottom[0]) and not (backslash and (len(topx) == 1)):
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
#        print(len(xfrom), len(yfrom), len(xto), len(yto))
#        if (len(xfrom) != len(xto)):
#            xfrom.append(0)
#            yfrom.append(0)
        shade = {'x1': robj.IntVector(xfrom), 'x2': robj.IntVector(xto),
                 'y1': robj.IntVector(yfrom), 'y2': robj.IntVector(yto)}
        shadf = robj.DataFrame(shade)
        return ggp.geom_segment(data=shadf, mapping=ggp.aes_string(x='x1',
                            xend='x2', y='y1', yend='y2'), colour=linecolour,
                            linetype='dashed', size=0.2)

    def xscale(numper):
        ggpxbreak = str([i*(numper/4.0) for i in range(5)]).strip('[]')
        #~todo~ handle data point count for month or year periods... how?
        periodtype = "data point"
        unittypes = OrderedDict([(60/cfg.timeUnit, 'hour'),
                                 (24, 'day'), (7, 'week')])
        for x,unit in unittypes.items():
            if (numper % x == 0):
                numper = int(numper/x)
                periodtype = unit
            else:
                break
        ggpxlabel='"0%","25%","50%","75%","100%\n({:,} {}{})"'.format(numper,
                                            periodtype, ('s', '')[numper == 1])
        return 'scale_x_continuous(breaks=c(' + ggpxbreak + '), label=c(' + \
                ggpxlabel + '))'

    aggdata()
    if nonstandard:
        if 'dataframe' in nonstandard:
            modedData = True
            mozdef = nonstandard['dataframe']
        detailData = cfg.getBool(nonstandard, 'plotDetail')
        if not detailData and 'plotDetail' in nonstandard:
            detailData = nonstandard['plotDetail']
            #~todo~ use this in future to create plot variations...
        includeHydro = cfg.getBool(nonstandard, 'includeHydro')
        onlyraw = cfg.getBool(nonstandard, keydata='onlyraw')
        if 'label' in nonstandard:
            anote = True
            if 'all' != nonstandard['label']:
                anotes = list(nonstandard['label'].split("|"))
        showshare = cfg.getBool(nonstandard, 'reshare', default=True)
        showquantity = cfg.getBool(nonstandard, 'energy')
        exports = cfg.getBool(nonstandard, 'exports')
        shading = cfg.getBool(nonstandard, 'shading', default=True)
        if 'custitle' in nonstandard:
            plotCusTitle = ": " + nonstandard['custitle']
        # 'include_zero' == expand_limits(y=0) no? ylim?
        # + if multiple plots, allow keep scales the same
        # switch to include exports on plot (& what @ charging info?)
        # allow config of residual ldc eg. solar or wind only etc.
        # ...for price info - scale_y_log10()
        # ...colour palette w/ scale_colour_brewer() or scale_colour_manual()
        # ...in aes_string use col='factor(...)'
        # ...try geom_smooth(ggp.aes_string(group='...'), method='lm')

    # wide & ordered data #
    #---------------------#
    if baseData:
        # sort data according to decending demand level for load duration curve
        if modedData:   #assume date range already applied
            ldf = mozdef.sort_values(by=cfg.COL_TOTAL, ascending=False)
        elif dateRange:
            ldf = df[dateRange[0]:dateRange[1]].sort_values(by=cfg.COL_TOTAL,
                                                            ascending=False)
        else:
            ldf = df.sort_values(by=cfg.COL_TOTAL, ascending=False)
        count = len(ldf)
        ldf['sortorder'] = range(1, count+1)
        orderlist = ['sortorder']
        totdem = ldf[cfg.COL_TOTAL].sum()
        # build a convenience dataframe that aligns all ldcs to one variable
        copylist = [x for x in ['sortorder', cfg.COL_TOTAL, cfg.COL_PRICE,
                                cfg.COL_EXPORT] if x in list(ldf)]
        ldf_wide = ldf[ copylist ].copy()
        #note that the datetime index remains... below could be used,
        #ldf_wide.reset_index(drop=True, inplace=True)
        #but this falls over when residual or adjusted index order included
        #~todo~ need to account for instance where data like price not present…
        # now calculate residual sans non-hydro renewables
        nonhydro = list(cfg.flatish(list(ldf), cfg.RENEWABLES_SET))
        if cfg.COL_HYDRO in nonhydro and not includeHydro:
            nonhydro.remove(cfg.COL_HYDRO)
        # IMPORTANT note: storage left out of this calc (for now)
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
        #~todo~ for dataframes w/o special adjustments use a pro-rata system
        adjldf = False
        difference = [0] * count
        for delta in filter(lambda x: x.endswith('.adjusted'), list(ldf)):
            if delta[:-9] in nonhydro:
                adjldf = True
                nonhydro.remove(delta[:-9])
                difference += ldf[delta].fillna( ldf[delta[:-9]] )
            elif delta[:-9] in list(ldf):   #handle residual adjustments
                difference += np.where(ldf[delta].isnull(), 0,
                                       ldf[delta] - ldf[delta[:-9]])
                #note that this is the delta that pushes adjusted curve down
        if adjldf:
            adjldf = not onlyraw   #calculate, but switch off if not requested
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
        elif not onlyraw:   #provide the pro-rata data, maybe
            ratarite = np.where(ldf[cfg.COL_EXPORT] == 0, 0,
                ldf[cfg.COL_EXPORT]/(ldf[cfg.COL_EXPORT] - ldf[cfg.COL_TOTAL]))
            #note that exports are -ve
            #exclude storage charging (for now)
            genList = [x for x in cfg.flatish(list(ldf)) if x not in
                            [cfg.COL_EXPORT, cfg.COL_IMPORT, cfg.COL_BATT_CHG,
                            cfg.COL_PUMPHYDRO_CHG]]
            renewables = list(cfg.flatish(list(ldf), cfg.RENEWABLES_SET))
            if not includeHydro and cfg.COL_HYDRO in renewables:
                renewables.remove(cfg.COL_HYDRO)
            for genData in genList:
                if genData in renewables:
                    difference += ldf[genData] - ratarite*ldf[genData]
                else:
                    difference += ratarite*ldf[genData]
                    #this will push residual DOWN
            ldf['adjusted'] = ldf[cfg.COL_TOTAL] - difference
            ldf.sort_values(by='adjusted', ascending=False, inplace=True)
            ldf['adjorder'] = range(1, count+1)
            orderlist.append('adjorder')
            totadj = ldf['adjusted'].sum()
            #test if worth displaying data i.e. > 1% difference
            #~todo~ could also display if adjusted/pro-rata is *less* than
            #residual
            adjldf = (totadj/totres) > 1.01
            adjust = "pro-rata"   #rename plot labels
            #complete convenience dataframe
            adjustlist = ldf['adjusted'].values
            adjustlist[::-1].sort()
            ldf_wide['adjusted'] = adjustlist
            ldf_wide['adjorder'] = ldf['adjorder']

    # long data #
    #-----------#
    if detailData:
        #~todo~ figure out how to handle this when pro-rata instead
        unneeded = cfg.LIMIT_LIST[:]
        unneeded.extend([cfg.COL_TOTAL, 'residual', 'adjusted', cfg.COL_PRICE])
        renewables = list(cfg.flatish(list(ldf), cfg.RENEWABLES_SET))
        renewables.extend( [x for x in list(ldf) if x.endswith('adjusted')
                                                   and x[:-9] in renewables] )
        unneeded.extend( renewables )
#        if not showexports:
        #remove from long data, no matter what value of showexports is
        unneeded.append( cfg.COL_EXPORT )
        ldfilter = ldf.drop(labels=unneeded, axis=1, inplace=False,
                                                     errors='ignore')
        #also make sure any non-renewables that have been adjusted are collated
        prorated = [x for x in list(ldfilter) if x.endswith('adjusted')]
        for delta in prorated:
            ldfilter[delta[:-9]] = ldfilter[delta].fillna(ldfilter[delta[:-9]])
        #~todo~ this(above) could be why output sometimes doesn't match the
        #simple adjusted load duration curve in ldf_wide... investigate
        ldfilter.drop(labels=prorated, axis=1, inplace=True, errors='ignore')
        # convert ldf to long format for more interesting plots...
        ldf_long = pd.melt(ldfilter, id_vars=orderlist, var_name='type',
                                                       value_name='generation')

    legendoff = robj.IntVector([1,1])
    #~todo~ provide flag to switch title & subtitle, maybe
    plotSubTitle = "load duration curve" + plotCusTitle
    commonTheme = [ggp.theme(**{"legend.justification": legendoff,
                                "legend.position": legendoff,
                                "legend.title": ggp.element_blank(),
                           "axis.text.x": ggp.element_text(hjust=1, vjust=1)}),
                   ggp.labs(title=plotTitle, subtitle=plotSubTitle,
                            x="{} minute periods".format(cfg.timeUnit),
                            y="generation ({})".format(cfg.genUnit)),
                   watermark()]

    while doPlot and baseData:
        # now plot
        #~todo~ some of this code is still using the r('') hack, clean it up
        #~todo~ consider using showexports to switch off export data
        activate_r(ldf_wide)   #instead of ldf directly
        pp = ggp.ggplot(rdf) + ggp.geom_line()
        if adjldf:
            pp += ggp.aes_string(x='sortorder', y=cfg.COL_TOTAL,
                          colour='"total"', linetype='"total"', size='"total"')
            pp += ggp.geom_line(ggp.aes_string(y='residual',
             colour='"'+resid+'"', linetype='"'+resid+'"', size='"'+resid+'"'))
            pp += ggp.geom_line(ggp.aes_string(y='adjusted',
                                colour='"'+adjust+'"', linetype='"'+adjust+'"',
                                size='"'+adjust+'"'))
            pp += r('guides(colour=guide_legend(reverse=T), ' \
             'linetype=guide_legend(reverse=T), size=guide_legend(reverse=T))')
        else:
            pp +=ggp.aes_string(x='sortorder',y=cfg.COL_TOTAL,colour='"total"')
            pp += ggp.geom_line(ggp.aes_string(y='residual',
                                               colour='"'+resid+'"'))
            pp += r('guides(colour=guide_legend(reverse=T))')
        #build x scale breaks & labels
        pp += r( xscale(count) )
        #theme stuff, legend tweaks, etc
        for add in commonTheme:
            pp += add
        pp += r('scale_colour_manual(values=c("total"="black","{}"="{}","{}"' \
                '="{}"))'.format(resid, resid_colour, adjust, adjust_colour))
        pp += r('scale_linetype_manual(values=c("total"="solid","{}"=' \
                '"dotdash","{}"="solid"))'.format(resid, adjust))
        pp += r('scale_size_manual(values=c("total"=0.5,"{}"=1,"{}"=' \
                '0.5))'.format(resid, adjust))

        ldfdata = [cfg.COL_TOTAL, 'residual']
        if adjldf:
            ldfdata.append('adjusted')
        count = len(ldf_wide)   #~todo~ probably not necessary

        # mins, maxs & others
        #~todo~ should really spin this off into a sub-procedure
        anocolour = "azure4"
        if anote:
            if 'baseload' in anotes:
                for x in ldfdata:
                #~todo~ figure out a good way to dodge lines & anything else
                    baseload = ldf_wide[x].iloc[-1]
                    pp +=ggp.geom_hline(yintercept=baseload, linetype='dashed')
                    pp += r('annotate("text", label="{:,.2f} {}", x={}, y={},'\
                            'hjust=0, vjust=-0.2)'.format(baseload,cfg.genUnit,
                                                       int(count/3), baseload))
            if adjldf and (ldf_wide['adjusted'].iloc[0] !=
                                                 ldf_wide['residual'].iloc[0]):
                print("warning: residual peak not the same as for adjusted...")
            if 'peak' in anotes:
                peak = ldf_wide[cfg.COL_TOTAL].iloc[0]
                pp += ggp.geom_segment(ggp.aes_string(x=0, xend=int(count/8),
                               y=peak, yend=peak), linetype='dotted', size=0.3)
                pp += r('annotate("text", label="{:,.2f} {}", x={}, y={}, ' \
                        'hjust=-0.1, vjust=0.5)'.format(peak, cfg.genUnit,
                                                        int(count/8), peak))
                peaketto = ldf_wide['residual'].iloc[0]
                pp += ggp.geom_segment(ggp.aes_string(x=0, xend=int(count/8),
                       y=peaketto, yend=peaketto), linetype='dotted', size=0.3)
                if 'delta' in anotes:
                    pp += ggp.geom_segment(ggp.aes_string(x=int(count/9),
                                xend=int(count/9), y=peak, yend=peaketto),
                                linetype='solid', colour=anocolour, size=0.3)
                    pp +=ggp.geom_point(ggp.aes_string(x=int(count/9), y=peak),
                                                              colour=anocolour)
                    pp += ggp.geom_point(ggp.aes_string(x=int(count/9),
                                                 y=peaketto), colour=anocolour)
                    #~todo~ find out how to do arrows via rpy2
                    pp += r('annotate("text", label="Δ = {:,.2f} {}", x={}, ' \
                            'y={}, hjust=-0.05, vjust=3, colour="{}")'.format(
                                                peak-peaketto, cfg.genUnit,
                                                int(count/9), peak, anocolour))
                else:
                    pp += r('annotate("text", label="{:,.2f} {}", x={}, y={},'\
                            'hjust=-0.1, vjust=0.5)'.format(peaketto,
                                          cfg.genUnit, int(count/8), peaketto))
            if 'percent5' in anotes:
                fivecent = int(0.05*count)
                pp +=ggp.geom_segment(ggp.aes_string(x=fivecent, xend=fivecent,
                             y=0, yend=ldf_wide[cfg.COL_TOTAL].iloc[fivecent]),
                             linetype='dotted', size=0.3)
                pp += r('annotate("text", label="5%", x={}, y=0, hjust=-0.1, '\
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
                    pp += r('annotate("text", label="{:,.2f} {}{}", x={}, ' \
                            'y={}, hjust=0, vjust=0.5, colour="{}")'.format(
                                            ygen, cfg.genUnit, xtra[curindex],
                                            fivecent*xoffset[curindex],
                                            ygen+yoffset[curindex], anocolour))
                    curindex += 1

        # renewables share info
        if showshare:
            totper = (totdem-totres)/totdem
            if adjldf:
                totadj = (totdem-totadj)/totdem
            else:
                totadj = np.NaN
            for x in reshare(ldf_wide[ldfdata].max(axis=0).max(),
                             ldf_wide[ldfdata].min(axis=0).min(), count,
                             [totper, totadj],
                             includeHydro, anote):
#                             includeHydro, (totper > 0.6) or anote):
# actually turns out that for a high RE share, below the curve is better.
                pp += r(x)
        #~todo~ alternate shading where solar & wind (& hydro) contribution
        #fills the area...! yes, do this ASAP
        if shading:
            safeout = cfg.getBool(keydata='slimshade', section='general',
                                  default=True)
            if adjldf and safeout:
                pp += slimshady(ldf_wide[cfg.COL_TOTAL], ldf_wide[('residual',
                          'resid_positive')[(ldf_wide['residual'] < 0).any()]])
                pp += slimshady(ldf_wide[cfg.COL_TOTAL], ldf_wide['adjusted'],
                                'tomato', True)
            else:
#                ldf_wide['resid_positive'] = np.where(ldf_wide.residual > 0,
#                                                        ldf_wide.residual, 0)
#needed to move this up the code...
                pp += ggp.geom_ribbon(ggp.aes_string(x='sortorder',
         ymin=('residual', 'resid_positive')[(ldf_wide['residual'] < 0).any()],
         ymax=cfg.COL_TOTAL), alpha=0.4, fill='deepskyblue', linetype=0,
         show_legend=False)
                if adjldf:
                    pp += ggp.geom_ribbon(ggp.aes_string(x='sortorder',
                               ymin='adjusted', ymax=cfg.COL_TOTAL), alpha=0.4,
                               fill="tomato", linetype=0, show_legend=False)
        if showquantity:
            anchor = count // 3
            sharetype = ('residual', 'adjusted')[adjldf]
            vertical = ldf_wide[sharetype].iloc[anchor - 1]
            #~todo~ will need to change sharetype to 'pro-rata' when relevant
            (quantity,scaletype) = scalenquant((totdem-totres)*cfg.timeUnit/60)
            pp += r('annotate("text", x={}, y={}, hjust=0, vjust=-3, ' \
                    'label="italic(\\"{:,.2f}{}h RE sans {}\\")", colour="{}"'\
                    ', parse="True")'.format(anchor, vertical, quantity,
                    scaletype, sharetype, ('darkgreen', 'darkgreen')[adjldf]))
            anchor = (count // 5)*2
            vertical = ldf_wide[cfg.COL_TOTAL].iloc[anchor - 1]
            (quantity, scaletype) = scalenquant(totdem * cfg.timeUnit/60)
            pp += r('annotate("text", x={}, y={}, hjust=0, vjust=-2, ' \
                    'label="italic(\\"{:,.2f}{}h total demand\\")", ' \
                    'colour="darkgreen", parse="True")'.format(anchor,
                                                vertical, quantity, scaletype))
        #~todo~ on adjusted 'crosshatch' work out good colour to use for text...
        #~todo~ ideally a background fill, but no geom_text available?
        if not showexports and (ldf_wide['residual'].iloc[-1] > 0):
            pp += ggp.ylim(0, robj.NA_Integer)
#need to investigate the use of annotation_custom(), but how to access grobTree
#& textGrob? ...does exist in rpy2.robjects.lib.grid.Grob
        pp.plot()
        
        #~todo~ clipping override ~ to allow labels in the margins, like #whtr
#need to hook into pp somehow first, but apparently use of this approach will
#remove the ability to use ggsave(). also, could use the new clip="off" option
#in coord_cartesian (but only available in latest version)
#        r('gt <- ggplot_gtable(ggplot_build(pp))')
#        r('gt$layout$clip[gt$layout$name == "panel"] <- "off"')
#        r('grid.draw(gt)')

        choice = proceed("ldc~residual.png")
        doPlot = False

        if detailData:
            #~todo~ implement display of export data with showexports
            activate_r(ldf_long)
            pp = ggp.ggplot(rdf) + ggp.aes_string(fill='type', y='generation',
                        x=('residorder', 'adjorder')[adjldf]) + ggp.geom_area()
#~todo~ smooth out the curves as an option -> investigate streamgraph
            #build x scale breaks & labels
            pp += r( xscale(count) )
            #theme stuff, legend tweaks, etc
            for add in commonTheme:
                pp += add
            #overwrite subtitle
            pp += ggp.labs(subtitle="load duration curve ~{} residual " \
                   "breakdown{}".format(("", " (" + adjust + ")")[adjldf],
                                        plotCusTitle))
            #use ggplot natural order
            nonre = sorted([x for x in list(ldfilter) if x not in orderlist])
            palette = [cfg.colourPalette[x] for x in nonre]
            relabel = [cfg.nicetype(x, template='()') for x in nonre]
            pp += ggp.scale_fill_manual(values=robj.StrVector(palette),
                                        labels=robj.StrVector(relabel))
            if showquantity:
                anchor = count // 4
                vertical = ldf_wide['residual'].iloc[anchor - 1]
                (quantity, scaletype) = \
                     scalenquant(ldf[cfg.COL_BATT_DIS].sum() * cfg.timeUnit/60)
                pp += r('annotate("text", x={}, y={}, hjust=-0.5, vjust=-2, ' \
                      'label="italic(\\"{:,.2f}{}h battery discharging\\")",' \
                      ' colour="darkgreen", parse="True")'.format(anchor,
                                                vertical, quantity, scaletype))

##        pp += r('scale_fill_manual("type", '\
##        'values=c("red","orange","blue","green","yellow","purple"), '\
#        'breaks=c("'+cfg.COL_BATT_DIS+'","'+cfg.COL_DIESEL+'","'+cfg.COL_GAS_CCGT+'","'+cfg.COL_GAS_OCGT+'","'+cfg.COL_GAS_STEAM+'","'+cfg.COL_IMPORT+'"))')
##        'labels=expression("gas"~italic("(CCGT)"),"two","three","four","five","six"))')
        #values=c("total"="black","{}"="{}","{}"="{}")
        #labels=expression(italic("(one)"),"two","three","four","five","six")
        #"scriptstyle(italic(\\"#whtr\\"))"


#    linkette = [neworder[x]+x for x in reorder]
#    relabel = [cfg.nicetype(x, template='()') for x in reorder]
    #~todo~ the colour scheme isn't quite so awful anymore, but make yet better
#    pp += ggp.scale_fill_manual(limit=robj.StrVector(linkette),
#                values=robj.StrVector(palette), labels=robj.StrVector(relabel))


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



            pp.plot()
            choice = proceed("ldc~{}.png".format("detail"))


def correlate(nonstandard=None):
    aggdata()
    corr_base = 'wind'
    corr_dep = 'imports'
    params_other = []
    loc_list = []
    plotType = 'basic'
    plotIndex = 0
    dotplot = True
    pricing = False
    logscale = False
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
        dotplot = cfg.getBool(nonstandard, 'dotplot', default=True)
        if 'thirdvar' in nonstandard:
            pricing = nonstandard['thirdvar'].startswith("price")
            logscale = (nonstandard['thirdvar'] == "pricelog")
    else:
        params = [corr_base, corr_dep, cfg.COL_TOTAL]
    #~todo~ in addition to multiple plots wrt to a single variable, could do
    #scatterplot matrices: 3 or more variables all compared to each other
    #~todo~ need to sanity check these variables are actually in dataset
    #~todo~ add ability to handle adjusted data
    #~todo~ combined correlation of import/export (assuming at least one is
    #always zero) wrt another variable
    
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
    commonTheme = [ggp.theme(**{"legend.position": robj.FloatVector([1,0.5]),
                           "legend.justification": robj.FloatVector([1,0.5])}),
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
        pricex = corr_base.startswith(cfg.COL_PRICE)
        pricey = corr_dep.startswith(cfg.COL_PRICE)
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
        #~todo~ implement a log scale on price colour point plots
            pp = ggp.ggplot(rdf)
            #assume x or y co-ords here won't be price data also
            if pricing:
                pp += ggp.aes_string(x=corr_base, y=corr_dep,
                                                          colour=cfg.COL_PRICE)
                colourDen = "Price\n({})".format(cfg.priceUnit)
            else:
                pp += ggp.aes_string(x=corr_base, y=corr_dep,
                                                          colour=cfg.COL_TOTAL)
                colourDen = "Demand\n({})".format(cfg.genUnit)
            pp += newrange
            pp += ggp.stat_density2d(ggp.aes_string(fill='..level..',
                                            alpha='..level..'), geom='polygon')
            pp += ggp.scale_fill_continuous(low='green', high='red')
            pp += ggp.guides(alpha='none')
#            pp += ggp.geom_point()
            pp += ggp.geom_point(ggp.aes_string(alpha=cfg.COL_TOTAL), size=.8)
            #~todo~ don't know why above works, it just does...
            rain = robj.StrVector(["red","yellow","green","lightblue",
                                   "darkblue"])
            pp += ggp.scale_colour_gradientn(colours=rain)
        else:
            continue
        if logscale:
            if pricex:
                pp += ggp.scale_x_log10()
            elif pricey:
                pp += ggp.scale_y_log10()
            dollarBill = "log~" + cfg.priceUnit
        else:
            dollarBill = cfg.priceUnit
        pp += ggp.labs(title=plotTitle, subtitle=plotSubTitle,
                       y="{} ({})".format(cfg.nicetype(corr_dep),
                                         (cfg.genUnit, dollarBill)[pricey]),
                       x="{} ({})".format(cfg.nicetype(corr_base),
                                         (cfg.genUnit, dollarBill)[pricex]),
                       colour=colourDen, fill='Density')
        #~todo~ format variant types properly
        for add in commonTheme:
            pp += add
        pp.plot()
        choice = proceed("correlation.png")


def boxplot(nonstandard=None):
    aggdata()
    reorder = []
    combos = {}
    #remove any adjustment data & unnecessary data like price & temperature
    params = [x for x in list(df) if not x.endswith('adjusted') or
                                        x not in [cfg.COL_PRICE, cfg.COL_TEMP]]
    #remove total as well, but #~todo~ could set flag to keep it
    if cfg.COL_TOTAL in params:
        params.remove(cfg.COL_TOTAL)
    if nonstandard:   #for selected or customised data
        if 'mods' in nonstandard:
            if 'showmin' in list(nonstandard['mods'].split("|")):
                addMin = True
        else:
            addMin = False
        if 'filter' in nonstandard:
            filter_list = list(nonstandard['filter'].split("|"))
            #check for combinations
            for parma in filter_list:
                mixdex = parma.find('[')
                if mixdex == -1:
                    reorder.append(parma)
                else:   #combination will be in [...]
                    reorder.append(parma[:mixdex])
                    combos[parma[:mixdex]] =list(parma[mixdex+1:-1].split("+"))
            #now remove excess generation types from list
            params[:] = [x for x in params if x in reorder or
                               x in [types for sublist in list(combos.values())
                                            for types in sublist]]
            #~todo~ there must be a simpler way to handle the lists in combos
    else:
        addMin = False
    #if combinations used, setup data
    if combos:
        sauce = df[params].copy()
        for newname, mix in combos.items():
            sauce[newname] = df[mix].sum(axis=1)
            #also drop original data unless also requested
            sauce.drop(labels=[x for x in mix if x not in reorder], axis=1,
                       inplace=True, errors='ignore')
        if dateRange:
            boxdf = pd.melt(sauce[dateRange[0]:dateRange[1]], var_name='type',
                            value_name='generation')
        else:
            boxdf = pd.melt(sauce, var_name='type',value_name='generation')
    elif dateRange:
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
    if addMin:
        pp += ggp.stat_summary(ggp.aes_string(label='..y..'), geom='text',
                               fun_y='min', colour='azure4',
                               position=ggp.position_jitter(width=0.3))
        #no position_nudge() available, alternately use r('') option
    if not reorder:
        reorder = list(cfg.flatish(params))
    relabel = [cfg.nicetype(x, template='nl') for x in reorder]
    pp += ggp.scale_x_discrete(limit=robj.StrVector(reorder),
                               label=robj.StrVector(relabel))
    palette = []
    for x in reorder:
        if x in combos:   #use colour of first type
            palette.append(cfg.colourPalette[ combos[x][0] ])
        else:
            palette.append(cfg.colourPalette[x])
    pp += ggp.scale_colour_manual(limit=robj.StrVector(reorder),
                                  values=robj.StrVector(palette))
    for add in commonTheme:
            pp += add
    pp.plot()
    choice = proceed("boxplot.png")


#~todo~ maybe turn this into a callable method to provide a plot of some kind?
def variability(data, grouped=False):
    order = pd.DataFrame()
    #~todo~ investigate alternate measures of 'variability'
    order['vary'] = data.min()/data.mean() \
                    + (data.quantile(0.75) - data.quantile(0.25)) \
                        / (data.max() - data.min())
    order['vary'] = order['vary'].fillna(0)
    basicord = order.sort_values(['vary']).index.tolist()
    if grouped:
        neword = []
        groupings = list(cfg.flatish(basicord, keepStructure=True))
        while len(basicord) > 0:
            neword.append(basicord.pop())   #take last item
            #now find group of this item
            if not neword[-1] in groupings:
                for gupete in groupings:
                #~todo~ will need to make this digging into tuples recursive
                    if isinstance(gupete, tuple) and neword[-1] in gupete[1]:
                    #now find other elements of this tuple
                        for other in reversed(basicord[:]):
                            if other in gupete[1]:
                                neword.append(other)
                                basicord.remove(other)
        return reversed(neword)
    else:
        return basicord


def timeseries(nonstandard=None):
#~todo~ improve the granularity of the time axis
#~todo~ make plot width bigger, and configurable
    aggdata()
    dabase = None
    flipneg = True
    co2profile = False
    plotCusTitle = ""
    #remove unnecessary data like price & temperature
    params = [x for x in list(df) if x not in [cfg.COL_TEMP, cfg.COL_PRICE]]
    #remove total as well, but #~todo~ could set flag to keep it
    #plus keep initially if using pro-rata method
    if cfg.COL_TOTAL in params and any(x.endswith('adjusted') for x in params):
        params.remove(cfg.COL_TOTAL)
    #make a copy of the original data
    if nonstandard and 'dataframe' in nonstandard:
        timedf = nonstandard['dataframe'].copy()
        droplist = [cfg.COL_TEMP, cfg.COL_PRICE]
        if any(x.endswith('adjusted') for x in list(timedf)):
            droplist.append(cfg.COL_TOTAL)
        timedf.drop(labels=droplist, axis=1, inplace=True, errors='ignore')
        #reset params
        params = list(timedf)
        if 'custitle' in nonstandard:
            plotCusTitle = "model: " + nonstandard['custitle']
    elif dateRange:
        timedf = df[dateRange[0]:dateRange[1]][params].copy()
    else:
        timedf = df[params].copy()
    #consolidate adjusted data
    adjust = [x for x in params if x.endswith('adjusted')]
    if adjust:
        for x in adjust:
            timedf[x[:-9]] = timedf[x].fillna(timedf[x[:-9]])
        timedf.drop(labels=adjust, axis=1, inplace=True, errors='ignore')
    else:
        negatives = list(cfg.flatish(list(timedf),
                    [cfg.COL_EXPORT, cfg.COL_BATT_CHG, cfg.COL_PUMPHYDRO_CHG]))
        negdel = timedf[negatives].sum(axis=1)
        ratarite = np.where(negdel == 0, 1,
                        timedf[cfg.COL_TOTAL]/(timedf[cfg.COL_TOTAL] - negdel))
        #note that imports should really remain unaltered, but leave for now
        #...charging data small enough to not really be a factor
        #plus currently not expecting import & export to be non-zero together
        #~todo~ implement a better algorythm at some point though
        #also, remove the totals column
        timedf.drop(labels=[cfg.COL_TOTAL], axis=1, inplace=True,
                    errors='ignore')
        therest = [x for x in list(timedf) if x not in negatives]
        for col in therest:
            timedf[col] = ratarite * timedf[col]
        #~todo~ could add a check here that total remains unaltered
    #customisation(s)
    if nonstandard:
        if 'bedrock' in nonstandard:
            dabase = nonstandard['bedrock']
        if 'aggregate' in nonstandard:
            addup = list(nonstandard['aggregate'].split("|"))
            for gentype in addup:   #amalgamate types into class type
                genparts = list(cfg.flatish(list(timedf),
                                            sourcelist=cfg.GROUPINGS[gentype]))
                timedf[gentype] = timedf[genparts].sum(axis=1)
                timedf.drop(labels=genparts, axis=1, inplace=True,
                            errors='ignore')
                params[:] = [x for x in params if x not in genparts]
            params.extend(addup)
        flipneg = cfg.getBool(nonstandard, 'flipneg')
        co2profile = cfg.getBool(nonstandard, 'ceeohtoo', default=True)
    #make sure only export data is -ve
    for dex in list(timedf):
        if (timedf[dex] <= 0).all() and (dex != cfg.COL_EXPORT) and flipneg:
            timedf[dex] = -timedf[dex]
    #get ordered measure of 'variability'
    bedrock = variability(timedf, dabase=='group')
    #de-index the time data
    timedf.reset_index(inplace=True)
    #generate wide format
    timedf_long = pd.melt(timedf, id_vars=[cfg.COL_TIMESTAMP], var_name='type',
                                           value_name='generation')
    #use this hack for now to establish the stack order for the plot
    #~todo~ come back & implement in a *better* way
    reorder = list(cfg.flatish(params))
    if dabase:
        neworder = dict((tup[1], str(tup[0]))
                                 for tup in list(enumerate( bedrock )))
    else:
        neworder = dict((tup[1], str(tup[0]))
                                 for tup in list(enumerate(reversed(reorder))))
    timedf_long['atype'] = [neworder[x]+x for x in timedf_long['type']]
    activate_r(timedf_long)
    commonTheme = [ggp.labs(title=plotTitle,
                            y="generation ({})".format(cfg.genUnit)),
                   ggp.theme(**{"axis.title.x": ggp.element_blank(),
                                "legend.position": "bottom",
                                "legend.title": ggp.element_blank()})]
    pp = ggp.ggplot(rdf) + ggp.aes_string(x=cfg.COL_TIMESTAMP, y="generation",
                                          fill="atype") + ggp.geom_area()
    palette = [cfg.colourPalette[x] for x in reorder]
    linkette = [neworder[x]+x for x in reorder]
    relabel = [cfg.nicetype(x, template='()') for x in reorder]
    #~todo~ the colour scheme isn't quite so awful anymore, but make yet better
    pp += ggp.scale_fill_manual(limit=robj.StrVector(linkette),
                values=robj.StrVector(palette), labels=robj.StrVector(relabel))
    for add in commonTheme:
            pp += add
    if len(plotCusTitle) > 0:
        pp += ggp.labs(subtitle=plotCusTitle)
    pp += watermark( str(timedf[cfg.COL_TIMESTAMP][0]) )
    pp.plot()
    choice = proceed("time.png")

    # now produce CO₂ profile of energy mix if requested
    #~todo~ complete this functionality
    if co2profile:
        pass


def co2intensity(nonstandard=None):
#~todo~ enhance to allow multiple carbon emissions profile - different states,
#       different scenarios/simulations, ...show internal, imported(when
#       non-zero - blank/null otherwise), & overall !! do this 1st!
#~todo~ option to show bulk carbon emissions instead
#~todo~ option to group by energy type & use generic intensity value
    showtrend = True
    aggdata()
    #filter both intensity hash & dataframe
    #note that export, total & storage charging all absent from this hash
    match = [x for x in list(df) if x in cfg.cohtoo.keys()]
    modcto = {keyfilter: cfg.cohtoo[keyfilter] for keyfilter in match}
    #also test for & keep any adjusted data...
    match.extend([x for x in list(df) if x[:-9] in match
                                        and x.endswith('adjusted')])
    if nonstandard:
        rawdata = list(nonstandard['cohtoo'].split("|"))
        if len(rawdata) == 0 or len(rawdata) % 2 != 0:
            print("...CO₂ emissions config bad, exiting.")
            return
        #override default emissions intensities
        for (gentype, value) in pairwise(rawdata):
            modcto[gentype] = value
        showtrend = cfg.getBool(nonstandard, 'showtrend', default=True)
        #imported emissions is simple single source for now
        #~todo~ enhance external emissions sourcing
        if 'nonlocal' in nonstandard:
            importdata = nonstandard['nonlocal']
    else:
        importdata = False
    if dateRange:
        codf = df[dateRange[0]:dateRange[1]][match].copy()
    else:
        codf = df[match].copy()
    if importdata:
        #make copy of import data & treat separately
        imQuant = codf[cfg.COL_IMPORT].replace(0, np.nan)
        codf.drop(labels=[cfg.COL_IMPORT], axis=1,inplace=True,errors='ignore')
        modcto.pop(cfg.COL_IMPORT)
        #source import CO₂ intensity i.e. 'internal co2' of source
        #~todo~ should check actually exporting from this source at relevant
        #times?
        #~todo~ retrieve actual imported intensity data, & error handling
#        cotherdf = pd.read_csv('../{}/co2.csv'.format(importdata), sep=';')
        #test for datetime index overlap (or not)
#        endpts = ((codf.index[0], codf.index[-1]), dateRange)[dateRange]
#        if all(x in cotherdf.index for x in endpts):
#            external = cotherdf['internal co2'][endpts[0]:endpts[1]]
#        else:
#            average = cotherdf['internal co2'].mean()
#            intervals = pd.infer_freq( cotherdf.index )
#            if intervals:
#                print("...existing frequency:", intervals)
#            ix = pd.DatetimeIndex(start=endpts[0], end=endpts[1],
#                                  freq=intervals)
#            codfredex = codf['internal co2'].reindex(ix, fill_value=average)
#            print("...incomplete CO₂ intensity data from {}, so where not " \
#            "available using default: {:,.1f}g/kWh".format(importdata,average))
        
        
        external = [900] * len(imQuant)
    else:
        print("...using default import CO₂ intensity: {}g/kWh".format(
                                        cfg.cohtoo.get( cfg.COL_IMPORT, 200 )))
    #~todo~ add test that no NaNs present? fill with zero?
    #handle adjusted data & alculate seperate internal & export values
    if any(x.endswith('adjusted') for x in match):
        adjustment = [x for x in list(codf) if x.endswith('adjusted')]
        #note that this delta will be exports + charging...
        #~todo~ wait? is it? double check
        #but intensity data is still correct
        exco2 = [0] * len(codf.index)
        exbulk = [0] * len(codf.index)
        for x in adjustment:
            print("...allocating portion of {} output to exported " \
                  "emissions".format(x[:-9]))
            #collate, determine exported co2 & then drop adjustment data
            adjust = codf[x].fillna(codf[x[:-9]])
            delta = codf[x[:-9]] - adjust
            exco2 += delta * modcto[x[:-9]]
            exbulk += delta
            codf[x[:-9]] = adjust
            match.remove(x)
        codf.drop(labels=adjustment, axis=1, inplace=True, errors='ignore')
        codf['exported emissions'] = exco2.replace(0, np.nan)
        codf['exported bulk'] = exbulk.replace(0, np.nan)
        codf['exported co2'] = (exco2 / exbulk).replace(0, np.nan)
    codf['emissions'] = codf[match].dot( pd.Series(modcto) )
    codf['bulk'] = codf[match].sum(axis=1)   #i.e. the total MegaWatts
    #then divide by what is: total +...
    #(+ exports + storage charging ...unless 'adjusted')
    codf['internal co2'] = codf['emissions'] / codf['bulk']
    #drop original data
    codf.drop(labels=match, axis=1, inplace=True, errors='ignore')
    if importdata:
        #put import data back in dataframe
        codf['imported co2'] = external.replace(0, np.nan)
        codf['imported emissions'] = imQuant*external
        codf['imported bulk'] = imQuant
        #save copy of internals
        codf['internal emissions'] = codf['emissions'].copy()
        codf['internal bulk'] = codf['bulk'].copy()
        #now amalgamate data
        codf['emissions'] += codf['imported emissions'].fillna(0)
        codf['bulk'] += codf['imported bulk'].fillna(0)
        codf['intensity'] = codf['emissions'] / codf['bulk']
    else:   #import data already included == internal
        #also make copy of CO₂ intensity
        codf['intensity'] = codf['internal co2'].copy()
    #save as csv(for use as exported CO₂)
    #~todo~ smarter save of data file, & error handling
    if os.path.isfile("co2.csv"):   #rename
        try:
            os.rename("co2.csv", "co2-prev.csv")
        except WindowsError:
            os.remove("co2-prev.csv")
            os.rename("co2.csv", "co2-prev.csv")
    codf.to_csv("co2.csv", sep=';')

    #de-index the time data
    codf.reset_index(inplace=True)
    #do plotting
    activate_r(codf)
    commonTheme = [ggp.labs(title=plotTitle, subtitle="CO₂ emission intensity",
                            y="gCO₂/kWh"),
                   ggp.theme(**{"axis.title.x": ggp.element_blank(),
#~todo~ put legend back in when multiple lines to display
#                                "legend.title": ggp.element_blank(),
                                "legend.position": "none"})]
    pp = ggp.ggplot(rdf) + ggp.aes_string(x=cfg.COL_TIMESTAMP, y='intensity',
                                     colour='"full"') + ggp.geom_line(size=0.3)
    pp += r('scale_colour_manual(values=c("full"="black"))')
    #~todo~ expand on this to include other data, as configured
    #add trend information
    if showtrend:
        pp += ggp.geom_smooth(method="lm", se=robj.BoolVector([False]),
                              colour="red")
        #~todo~ extract values of fitted line endpoints & display on plot
        #~todo~ more sophistication in fitting method, auto? or what?
        #~todo~ instead of a fitted line, calc a running average (3 months?)
    
    
    for add in commonTheme:
            pp += add
    pp += watermark( str(codf[cfg.COL_TIMESTAMP][0]) )
    pp.plot()
    choice = proceed("co2.png")


#~todo~ complete this
def trend(nonstandard=None):
    pass


def simulation(nonstandard=None):
    def testot():
        newlist = [x for x in list(simdf) if not x.endswith('adjusted') and
                         x not in [cfg.COL_TOTAL, cfg.COL_PRICE, cfg.COL_TEMP]]
        newtotal = simdf[newlist].sum(axis=1)
        #note: simple subtraction will generally result in delta of ~1e-13
        closenuff = np.isclose(newtotal, simdf[cfg.COL_TOTAL])
        if all(closenuff):
            print(" ~ new totals within delta (1e-08): OK ~")
        else:
            print("!!! unacceptable delta from original total demand:")
            print(simdf[cfg.COL_TOTAL][~closenuff])
            print(simdf[~closenuff])
            print("--------------------------------------------------")
            print(newtotal[~closenuff])
            print("-------------------actual-delta-------------------")
            delta = newtotal - simdf[cfg.COL_TOTAL]
            print(delta[~closenuff])

    def rebalance(balance, prorata=False):
        # calculate minimum non-renewable delta level due to inertia req
        #~todo~ should make this less South Australia specific
        if not prorata:
            minertia = simdf[cfg.COL_GAS_STEAM] + simdf[cfg.COL_GAS_CCGT] \
                        - inertia
            previousMin = minertia.sum()
            minertia[minertia < 0] = 0   #this *should* be redundant
            if previousMin < minertia.sum():
                print("! inertia level set higher than actual production in " \
                      "data.")
        # reduce the generation types as defined in 'meritorder'
        for each in meritorder:
            delta = np.where(balance > simdf[each], simdf[each], balance)
            delta[delta < 0] = 0   #just to be sure
            #extra check for the inertia types
            if not prorata:
                if each in [cfg.COL_GAS_STEAM, cfg.COL_GAS_CCGT]:
                    delta = np.where(delta > minertia, minertia, delta)
                    minertia -= delta
            # decrease exports & conventional gen
            balance -= delta
            #also track any 'adjusted' data
            if each + '.adjusted' in list(simdf):
                adjustment = simdf[each] - simdf[each + '.adjusted'].fillna(
                                                                   simdf[each])
                adjustment -= delta
                adjustment[adjustment < 0] = 0
                #test if this becomes zeroed out
                if any(adjustment):   #i.e. still have non-zero values
                    simdf[each + '.adjusted'] = np.where(adjustment == 0,
                                              np.nan, simdf[each] - adjustment)
                else:
                    #adjustment no longer necessary for this gen type
                    print('...column for "{}" has zeroed out - removed from ' \
                          'dataframe'.format(each + '.adjusted'))
                    simdf.drop(labels=[each + '.adjusted'], axis=1,
                                                 inplace=True, errors='ignore')
            simdf[each] -= delta
        return balance

    aggdata()
    if nonstandard:
        rawdata = list(nonstandard['model'].split("|"))
        if len(rawdata) == 0 or len(rawdata) % 2 != 0:
            print("...no good configuration data, exiting.")
            return
        model = dict(pairwise(rawdata))
        meritorder = list(nonstandard['meritorder'].split("|"))
        #~todo~ could automatically determine the minimum inertia required
        inertia = float(nonstandard.get('inertia', 0))
        #allow for timeseries plot to be skipped (esp for long time period)
        showtime = cfg.getBool(nonstandard, 'showtime', default=True)
    else:
        print("...no configuration data, exiting.")
        return
    if dateRange:
        simdf = df[dateRange[0]:dateRange[1]].copy()
    else:
        simdf = df.copy()
    #test for pro-rata data
    prorata = not any(x.endswith('adjusted') for x in list(simdf))
    ###
    # multiply simulated generation types
    ###
    xport = abs(simdf[cfg.COL_EXPORT])   #use absolute values of export
    modelTitle = ', '.join(['{0} +{1:.0%}'.format(cfg.nicetype(key,
              template='()'), float(value)) for (key, value) in model.items()])
    for gentype, multiple in model.items():
        # balance demand curve with excess -> exports
        testneg = simdf[gentype] < 0   #do not multiply negative values though
        modgentype = simdf[gentype].copy()
        if any(testneg):
            modgentype[testneg] = 0
        xport += modgentype * float(multiple)
        xport = rebalance(xport, prorata)
        # make sure raw gentype data has simple multiple
        modgentype = modgentype * (1 + float(multiple))
        modgentype[testneg] = simdf[gentype]   #add negative values back in
        simdf[gentype] = modgentype
    # reset export data & relevant adjustments
    simdf[cfg.COL_EXPORT] = -xport[:]
    for each in [x for x in list(simdf) if x[:-9] not in model.keys() and
                                           x.endswith('adjusted')]:
        #use 'xport' now as the total adjustment needed
        xport -= simdf[each[:-9]] - simdf[each].fillna(simdf[each[:-9]])
    #note: even in a pro-rata dataset, from this point excess renewables are
    #being exported... so use adjustment approach
    genlist = list(model.keys())
    genum = len(genlist)
    if genum == 1:
        gentype = genlist[0]
        simdf[gentype + '.adjusted'] = np.where(xport == 0, np.nan,
                                                simdf[gentype] - xport)
    else:   #pro-rata adjustment of renewables with exports
        renewtot = simdf[genlist].sum(axis=1)
        for gentype in genlist:
            simdf[gentype + '.adjusted'] = np.where(xport == 0, np.nan,
                                           simdf[gentype]*(1 - xport/renewtot))
    # display current mix
    #...and sanity check against actual total demand
    testot()
    print("...new energy mix with raw additions:", model)
    if showtime:
        timeseries( {'dataframe': simdf, 'custitle': modelTitle,
                     'ceeohtoo': True} )
    #...also run load duration curves
    print("...and load duration curve info")
    ldc( {'dataframe': simdf, 'custitle': modelTitle} )
    #~todo~ should start including generation of residual breakdown once robust
    ###
    # re-route remaining exports into battery charging, while tracking storage
    # levels
    ###
#    simdf[cfg.COL_BATT_CHG] += simdf[cfg.COL_EXPORT]
    #...strictly speaking should do this but leave off to make plotting simpler
    #note: important that exports is non-nan ~todo~ double-check this
    xport = -simdf[cfg.COL_EXPORT]
    renlist = list(cfg.flatish(list(simdf), cfg.RENEWABLES_SET))
    #calculate amount of non-renewables in export data
    #note: not all renewables are necessarily in model.keys()
    notneeded = [x for x in list(simdf) if x[:-9] in renlist and
                                           x.endswith('adjusted')]
    for each in notneeded:
        xport -= simdf[each[:-9]] - simdf[each].fillna(simdf[each[:-9]])
        #...and reset to amount *not* exported/sent to charging
        simdf[each[:-9]] = simdf[each].fillna(simdf[each[:-9]])
    simdf.drop(labels=notneeded, axis=1, inplace=True, errors='ignore')
    #amount of energy in MWh (or whatever unit raw data comes in)
    chgfactor = cfg.timeUnit/60
    tocharging = -xport - simdf[cfg.COL_EXPORT]
    simdf[cfg.COL_EXPORT] = -xport   #reset export data
    renport = tocharging * chgfactor
    simdf['energysilo'] = renport.cumsum()   #cumulative total storage
    ###
    # re-balance supply by discharging from battery
    ###
    #determine necessary amount of discharging to reduce non-renewables
    gap = simdf[cfg.COL_TOTAL] - simdf[renlist].sum(axis=1) - inertia
    if (gap < 0).any():
        print("warning: attempting to discharge when not required...")
        gapcrit = gap < 0
#        print(simdf[gapcrit])
        gap[gapcrit] = 0   #clear these cases to keep it simple
    #...and if sufficient storage is available
    print("...attempting simple discharge")
    gaphours = chgfactor * gap
    firstry = simdf['energysilo'] - gaphours.cumsum()
    #~todo~ probably should be shifted one position, but not likely to be used
    if (firstry < 0).any():
        print("...re-do discharge with actual capacity taken into account")
        #~todo~ figure out the true/better pythonic way to implement this...
        retry = []
        available = 0
        #note: below is in MW, not MWh
        for need, extra in zip(gap, tocharging):
            if available > need:
                dischg = need
                available -= need
            else:   #empty the battery
                dischg = available
                available = 0
            retry.append( dischg )
            available += extra
        simdf['temp'] = retry   #converts to Series with correct indexing
        simdf[cfg.COL_BATT_DIS] += retry
        leftovers = rebalance(simdf['temp'], prorata)
        simdf.drop(labels=['temp'], axis=1, inplace=True, errors='ignore')
        simdf[cfg.COL_BATT_DIS] -= leftovers
        if any(leftovers):   #modified during rebalancing
            reover = chgfactor * (leftovers - retry)
            simdf['energysilo'] += reover.cumsum()
        else:
            reover = chgfactor * np.asarray(retry)
            simdf['energysilo'] -= reover.cumsum()
    else:
        simdf[cfg.COL_BATT_DIS] += gap
        leftovers = rebalance(gap, prorata)
        simdf[cfg.COL_BATT_DIS] -= leftovers
        if any(leftovers):   #modified during rebalancing
            lefthours = chgfactor * leftovers
            simdf['energysilo'] = firstry + lefthours.cumsum()
        else:
            simdf['energysilo'] = firstry
    # again display current mix
    #...and sanity check against actual total demand
    storedf = simdf[['energysilo']].copy()
    storedf['energydelta'] = storedf['energysilo'].diff()
    storedf.reset_index(inplace=True)
    simdf.drop(labels=['energysilo'], axis=1, inplace=True, errors='ignore')
    testot()
    print("...energy mix with storage in effect:")
    if showtime:
        timeseries( {'dataframe': simdf, 'custitle': modelTitle,
                     'ceeohtoo': True} )
    print("...and load duration curve info")
    ldc( {'dataframe': simdf, 'plotDetail': 'rezdetail', 'energy': 'True',
          'custitle': modelTitle + " + storage"} )
    #...and redo this time with charging data included
    print("...energy mix including battery charging data:")
    simdf[cfg.COL_BATT_CHG] -= tocharging   #note: -ve in the data
    if showtime:
        timeseries( {'dataframe': simdf, 'custitle': modelTitle,
                     'flipneg': 'off', 'ceeohtoo': True} )

    # finally, show profile of battery dis/charge
    activate_r(storedf)
    commonTheme = [ggp.labs(title=plotTitle,
                            subtitle="energy storage with " + modelTitle,
                            y="Storage ({}h)".format(cfg.genUnit)),
                   ggp.theme(**{"axis.title.x": ggp.element_blank()})]
    pp = ggp.ggplot(rdf) + ggp.aes_string(x=cfg.COL_TIMESTAMP, y='energysilo')
    pp += ggp.geom_line(colour=cfg.colourPalette.get(cfg.COL_BATT_DIS,
                                                     'slateblue'))
    #indicate max values + max dis/charge
    #~todo~ smarter code to make sure text is not clipped
    stordex, value = max(enumerate(storedf['energysilo']), key=lambda x: x[1])
    when = storedf[cfg.COL_TIMESTAMP][stordex]
    (quantity, scaletype) = scalenquant(value)
    pp += r('annotate("text", label="italic(\\"{:,.2f}{}h\\")", hjust=0.5, ' \
            'vjust=-0.5, x=as.POSIXct("{}"), y={}, colour="slateblue", ' \
            'parse="True")'.format(quantity, scaletype, when, value))
#    pp += ggp.geom_point(ggp.aes_string(x=robj.POSIXct([when]), y=value),
#                         colour='mediumblue')
    #this is funky, offsets to wrong spot & point is weird looking...
    #~todo~ investigate why, but for now do this,
    pp += r('annotate("point", x=as.POSIXct("{}"), y={}, ' \
            'colour="slateblue")'.format(when, value))
    stordex, value = max(enumerate(storedf['energydelta'].fillna(0)),
                         key=lambda x: x[1])
    when = storedf[cfg.COL_TIMESTAMP][stordex]
    (quantity, scaletype) = scalenquant(value * 60/cfg.timeUnit)
    #~todo~ value has to be reset too, so redo this code properly at some point
    value = storedf['energysilo'][stordex]
    pp += r('annotate("text", label="italic(\\"+{:,.2f}{}\\")", hjust=1.1, ' \
            'vjust=-0.5, x=as.POSIXct("{}"), y={}, colour="slateblue", ' \
            'parse="True")'.format(quantity, scaletype, when, value))
    pp += r('annotate("point", x=as.POSIXct("{}"), y={}, ' \
            'colour="slateblue")'.format(when, value))
    stordex, value = min(enumerate(storedf['energydelta'].fillna(0)),
                         key=lambda x: x[1])
    when = storedf[cfg.COL_TIMESTAMP][stordex]
    (quantity, scaletype) = scalenquant(abs(value * 60/cfg.timeUnit))
    value = storedf['energysilo'][stordex]
    pp += r('annotate("text", label="italic(\\"-{:,.2f}{}\\")", hjust=0.2, ' \
            'vjust=-0.5, x=as.POSIXct("{}"), y={}, colour="slateblue", ' \
            'parse="True")'.format(quantity, scaletype, when, value))
    pp += r('annotate("point", x=as.POSIXct("{}"), y={}, ' \
            'colour="slateblue")'.format(when, value))
    for add in commonTheme:
        pp += add
    pp += watermark( str(storedf[cfg.COL_TIMESTAMP][0]) )
    pp.plot()
    choice = proceed("storage.png")


# +++++++++++++++++++++++++++
# +++ active status tests +++
# +++++++++++++++++++++++++++

def data_present():
    return not df.empty


# +++++++++++++++++++++
# +++ data sourcing +++
# +++++++++++++++++++++

def new_column(unmatched):

    def matchcount(name):
        lowname = name.lower()
        count = 0
        for tagtest in tags:
            if tagtest in lowname:
                count += 1
        return count

    # split text on which to tag
    tags = [x.lower() for x in re.findall(r'[a-zA-Z0-9]+', unmatched)]
    # track occurance of tags in unused column types
    available = cfg.flatish(colRename.values(), inverse=True)
    coloptions = dict((column, matchcount(column)) for column in available)
    # test if no matches
    if all(v == 0 for v in coloptions.values()):
        print("...no likely match found for", unmatched)
        return
    # find key with greatest count value as new column
    #~todo~ maybe handle case when equal max values present
    return max(coloptions.keys(), key=lambda k: coloptions[k])


def load_csv(datasource):
    global colRename, colOrigTimestamp, dataGenList, dataFill, backFill, \
           filterList, fillList
    print("...reading data from", datasource)
    if not colRename:   #setup column name translation
        print("...setting data parameters")
        colRename = dict(cfg.config['data.columns'])
        # also extract column name for timestamp in source data file
        #~todo~ also add functionality for multi-column source index
        #eg. date & time in separate columns
        colOrigTimestamp = next((raw for raw, new in colRename.items()
                                 if new == cfg.COL_TIMESTAMP), None)
        del colRename[colOrigTimestamp]
        #now test that timestamp index isn't numeric for blank column name
        #...and convert to integer value that specifies correct column
        try:
            blankdex = int(colOrigTimestamp)
            colOrigTimestamp = blankdex   #typically going to be '0' -> 0
        except ValueError:
            pass   #do nothing
        # check for original columns to be filtered out
        if 'filter' in colRename:
            filterList = colRename.get('filter').split('|')
            del colRename['filter']
        # establish back or forward fill
        if 'fill' in colRename:
            fillList = colRename.get('fill').split('|')
            del colRename['fill']
            #setup fill list for combined & renamed data
            dataFill = [new for old, new in colRename.items()
                            if old in fillList]
            backFill = cfg.getBool(keydata='backfill', section='general')
        # check for data that needs to be split
        #note: assume only two, first takes +ve values, second -ve
        origkeys = list(colRename.keys())   #make a copy
        for key in origkeys:
            value = colRename[key]
            if '|' in value:
                splitlist = value.split('|')   #expect only two values
                #now build back into colRename dictionary
                colRename[key + '+'] = splitlist[0]
                colRename[key + '-'] = splitlist[1]
                del colRename[key]
                #mark original column for deletion
                if filterList:
                    filterList.append(key)
                else:
                    filterList = [key]
    if not dataGenList:   #sort types into prefered order
        dataGenList = list(cfg.flatish( colRename.values() ))
    # read in the data
    #~todo~ provide even greater customisation by allowing config to pass in
    #hash of parameters ...this would leverage the pandas capabilities
    if cfg.getBool(keydata='smartparse', section='general'):
        dateformat = cfg.config['general'].get('dateformat', cfg.dateFormat)
        dateparser = lambda x: pd.datetime.strptime(x, dateformat)
        tdf = pd.read_csv(datasource, sep=',', parse_dates=[colOrigTimestamp],
                          date_parser=dateparser, index_col=[colOrigTimestamp])
        #~todo~ datetimes are just the *worst*, hack here to fix for now
        tdf.index = pd.to_datetime(tdf.index, format=dateformat, utc=True)
#    elif isinstance(colOrigTimestamp, int):
#probably not necessary...
    else:
        tdf = pd.read_csv(datasource, sep=',', parse_dates=[colOrigTimestamp],
                          index_col=[colOrigTimestamp])
    #~todo~ for data that has timezone offset -> reset to local time
    #~todo~ test that data is either always -ve or +ve
    # fill in specified data columns (eg 30min period -> 5min data)
    for col in fillList:
        tdf[col].fillna(method=('ffill', 'bfill')[backFill], inplace=True)
    # if required, split raw data
    for key, value in colRename.items():
        if not key.endswith('+'):
            continue
        okey = key[:-1]
        xiport = False
        print("...splitting {} column".format(okey))
        if value == cfg.COL_EXPORT:   #note: whtr assumes exports are -ve
            if cfg.getBool(keydata='expoz', section='general'):
            #~todo~ need to expand this polarity switch for uncombined data
            #eg in .whtr (where exports are provided as +ve values)
            #  NETINTERCHANGE : exports|imports
            #  but also expoz : True in section general
                tdf[okey] = -tdf[okey]
                xiport = True
            else:
                print("!!! handling export data as +ve?")
        #split the column into -ve & +ve
        tdf[okey + ('+','-')[xiport]] = np.where(tdf[okey] > 0, tdf[okey], 0)
        tdf[okey + ('-','+')[xiport]] = np.where(tdf[okey] < 0, tdf[okey], 0)
    # relabel columns
    tdf.index.names = [cfg.COL_TIMESTAMP]
    tdf.rename(columns=colRename, inplace=True)
    # remove specified filtered columns (& potentially the split ones too)
    if filterList:
        tdf.drop(filterList, axis=1, inplace=True)
    # remove & double-check empty data columns
    discard = [x for x in list(tdf) if x not in colRename.values()]
    for check in discard[:]:
        if (tdf[check] != 0).any() and not all(tdf[check].isnull()):
            print("...non-zero value in", check)
            potential = new_column(check)
            if potential is not None:
                print("...establishing new column for data type:", potential,
                      "(config file will be updated)")
                discard.remove(check)
                tdf.rename(columns={check: potential}, inplace=True)
                colRename[check] = potential
                cfg.config.set('data.columns', check, potential)
                #this will be written to disk by lacedata()
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
    adjustor = cfg.config['data.customised'].get(cfg.COL_EXPORT, False)
    if adjustor:   #expected to be 'wind'
        if (abs(tdf[cfg.COL_EXPORT]) > abs(tdf[adjustor])).any():
        #note: -ve values for wind do happen - see South Australia 2018-04-30
        # 12:50 where 'generation' hits -0.58MW
        # AND a long stretch during 2018-06-09 !!!
            #hack a psuedo pro-rata balancing of the export amount
            #~todo~ implement a better approach at some point
            #generate mask of rows to use modified adjustment on
            criteria = tdf[adjustor] + tdf[cfg.COL_EXPORT]*2 < 0
            #determine candidates for adjustment
            justGenList = dataGenList[:]
            justRenewables = list(cfg.flatish(dataGenList,
                                  sourcelist=cfg.RENEWABLES_SET))
            justRenewables.append(cfg.COL_IMPORT)
            justGenList[:] =[x for x in justGenList if x not in justRenewables]
            justgen = tdf[justGenList]
            genorder = justgen[criteria].sum().sort_values(
                                                 ascending=True).index.tolist()
            prorata = [adjustor]
            while (abs(tdf[cfg.COL_EXPORT]) > tdf[prorata].sum(axis=1)).any():
                prorata.append( genorder.pop() )
            print("! {} times {} generation not sufficient to be exported..." \
                  "\nusing {} to balance exports with actual supply.".format(
                                             sum(criteria), adjustor, prorata))
            #pro-rata mix with original adjustor
            prototal = np.where(criteria, tdf[prorata].sum(axis=1), np.nan)
            #modify for actual negative generation
            neggen = tdf[adjustor] < 0
            if any(neggen):
                print("also handling -ve generation in original data... " \
                      "which will remain unchanged.")
                #clear -ve data from total
                prototal = np.where(neggen, prototal - tdf[adjustor], prototal)
            for adjut in prorata:
                prodelta = np.where(criteria,
                         tdf[adjut]*(1 + tdf[cfg.COL_EXPORT]/prototal), np.nan)
                #combine seperate approaches into a single result
                if adjut == adjustor:
                    #but make sure -ve gen data unchanged
                    if any(neggen):
                        prodelta = np.where(neggen, np.nan, prodelta)
                    normal = np.where(tdf[cfg.COL_EXPORT] != 0,
                                   tdf[adjustor] + tdf[cfg.COL_EXPORT], np.nan)
                    tdf[adjustor + '.adjusted'] = np.where(criteria, prodelta,
                                                                     normal)
                else:
                    tdf[adjut + '.adjusted'] = prodelta
        else:
            tdf[adjustor + '.adjusted'] = tdf.apply(
                          lambda x: x[adjustor] + x[cfg.COL_EXPORT]
                          if (x[cfg.COL_EXPORT] != 0) else np.nan, axis=1)
        # sanity checks
        whackamole = tdf[adjustor + '.adjusted'] < 0
        if whackamole.any():
            print("!!! adjustment of {} has led to -ve generation...?".format(
                                                                     adjustor))
            if all(tdf[adjustor][whackamole] < 0):
                print("ok, nothing to see here, *original* generation data" \
                      " is -ve.")
            else:
                print(tdf[whackamole])
        # IMPORTANT: below is a hack, subtracting battery charging out of
        # wind output - small numbers so not a big deal, but temporary fix
        # otherwise, weird jitter in the residual data...
        #~todo~ need a more sensible, fairer way to deal with this
        chgnonzero = tdf[cfg.COL_BATT_CHG] != 0
        if (abs(tdf[chgnonzero][cfg.COL_BATT_CHG]) >
                                              tdf[chgnonzero][adjustor]).any():
            print("! battery charging actually exceeds wind output...")
        hack = tdf[adjustor + '.adjusted'].fillna(tdf[adjustor]) \
                + tdf[cfg.COL_BATT_CHG]
        tdf[adjustor + '.adjusted'] = np.where(hack == tdf[adjustor],
                                               np.nan, hack)
    #alternate approach would be to pro-rata reduction in all generation for
    #export amount
    #~todo~ implement this...
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
            composition = list(cfg.flatish(list(df),
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
    if not df.agged:
        aggs = cfg.config['general'].get('aggregate', "").split()
        #~todo~ parts of the following code are untested...
        if aggs:
            for newcol in aggs:
                comp = list(cfg.flatish(list(df), cfg.GROUPINGS.get(newcol)))
                if not comp:   #zero-length list
                    continue
                df[newcol] = df[comp].sum(axis=1)
                df.drop(labels=comp, axis=1, inplace=True, errors='ignore')
                #now do similar for any adjusted data
                if (len(comp) == 1) and (comp[0] + '.adjusted' in df):
                    df.rename(columns={comp[0] + '.adjusted':
                                           newcol + '.adjusted'}, inplace=True)
                else:
                    #do it this way in order to handle NaNs
                    oldata = list(filter(lambda x: x.endswith('.adjusted') and
                                                   x[:-9] in comp, list(df)))
                    if len(oldata) == 0:
                        continue
#                    print(oldata)
                    df[newcol + '.adjusted'] = df[oldata].sum(axis=1)
                    df.drop(oldata, axis=1, inplace=True, errors='ignore')
        df.agged = True


def lacedata(datalist):
    global df
    if len(datalist) == 0:
        print(" * no data to process *")
        return
    currentFiles = list(filter(bool, cfg.config['data.processed'].get('files',
                                                               '').split(",")))
    if not df.empty:
        df.reset_index(inplace=True)
    for dfile in datalist[:]:
        #~todo~ maybe pre-sort according to date range, use filename for clues?
        #~todo~ also need to double check time period constant ie. 5 minutes
        #~todo~ investigate DatetimeIndex class
        tdf = load_csv(dfile)
        #~todo~ node.execute() will still fail, so fix that...
        currentFiles.append(dfile)   #add to .whtr list
        datalist.remove(dfile)   #and remove datafile from the list
        tdf.reset_index(inplace=True)   #make it easier to merge
        if df.empty:
            df = tdf
        else:   #join tdf to df
            #~todo~ consider placing tdf`s into a list & appending once
            df = df.append(tdf, ignore_index=False)
            # remove (identical) duplicate rows
            dupcount = df.duplicated().sum()
            #~todo~ eff-imp: could retain series, rather than re-run check here
            if dupcount:
                print("...removing {} duplicate rows".format(dupcount))
                df.drop_duplicates(inplace=True)
            # double check & filter for just duplicated timestamps
            dupcount = df.duplicated(cfg.COL_TIMESTAMP).sum()
            if dupcount:
            #...this appears to be the solar,rooftop data that is offset by
            # 5 minutes b/w the different datafiles
            #~todo~ add feature to review the differences b/w data sets
#                testdup = df.duplicated(cfg.COL_TIMESTAMP, keep=False)
#                print(df[testdup].sort_values(by='datetime'))
                print("...{} more rows with same timestamp also " \
                      "removed".format(dupcount))
                df.drop_duplicates(cfg.COL_TIMESTAMP, inplace=True)
            # second phase data fill in for combined data...
            for col in dataFill:
                df[col].fillna(method=('ffill', 'bfill')[backFill],
                               inplace=True)
    #~todo~ run sanity checks on data eg. 5 minute intervals consistent
    df.set_index(cfg.COL_TIMESTAMP, inplace=True)
    df.agged = False
    # finally, write to disk
    df.to_csv(cfg.config['general'].get('dbname', "whtr.csv"),
                                        sep=';')   #"revenge is mine"
    cfg.config.set('data.processed', 'files', ','.join(map(str, currentFiles)))
    cfgfile = open(".whtr", 'w')
    cfg.config.write(cfgfile)
    cfgfile.close()
    #~todo~ make sure backup is kept as well
    # then aggregate
    aggdata()


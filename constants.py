import configparser
import re

# note: this whole part is a first pass, quick & nasty. please don't judge me.

COL_TIMESTAMP = 'datetime'
COL_PRICE = 'price'
COL_TEMP = 'temperature'
COL_TOTAL = 'total'
COL_EXPORT = 'exports'
COL_IMPORT = 'imports'
COL_HYDRO = 'hydro'
TYPE_WIND = 'wind'
COL_WIND_ON = 'wind,onshore'
COL_WIND_OFF = 'wind,offshore'
TYPE_SOLAR = 'solar'
COL_SOLAR_ROOF = 'solar,rooftop'
COL_SOLAR_UTIL = 'solar,utility'
COL_SOLAR_THERMAL = 'solar,thermal'
TYPE_RENEWABLES = 'renewables'
COL_NUCLEAR = 'nuclear'
COL_BIOMASS = 'biomass'
COL_GEOTHERM = 'geothermal'
COL_OIL = 'oil'
COL_DIESEL = 'diesel'
TYPE_GAS = 'gas'
COL_GAS_CCGT = 'gas,CCGT'
COL_GAS_OCGT = 'gas,OCGT'
COL_GAS_STEAM = 'gas,steam'
COL_GAS_REP = 'gas,reciprocating'
TYPE_COAL = 'coal'
COL_COAL_BROWN = 'coal,brown'
COL_COAL_BLACK = 'coal,black'
TYPE_STORAGE = 'storage'
COL_BATT_CHG = 'battery,charging'
COL_BATT_DIS = 'battery,discharging'
COL_PUMPHYDRO_CHG = 'pumped hydro,charging'
COL_PUMPHYDRO_DIS = 'pumped hydro,discharging'
#~todo~ add auxiliary types & ability to rename them for future flexibility
#~todo~ would auxilary tech like synchronous condensers fit here?

#note: by specifying any of these global types(eg gas) in .whtr, the variants
#will be aggregated.
COAL_SET = (COL_COAL_BROWN, COL_COAL_BLACK)
GAS_SET = (COL_GAS_STEAM, COL_GAS_OCGT, COL_GAS_CCGT, COL_GAS_REP)
SOLAR_SET = (COL_SOLAR_UTIL, COL_SOLAR_THERMAL, COL_SOLAR_ROOF)
WIND_SET = (COL_WIND_ON, COL_WIND_OFF)
RENEWABLES_SET = (COL_HYDRO, TYPE_WIND, TYPE_SOLAR, COL_GEOTHERM)
#~todo~ also consider splitting hydro into large & small ala California...
STORAGE_SET =(COL_BATT_DIS, COL_PUMPHYDRO_DIS, COL_BATT_CHG, COL_PUMPHYDRO_CHG)
GROUPINGS = {TYPE_COAL: COAL_SET, TYPE_GAS: GAS_SET, TYPE_SOLAR: SOLAR_SET,
             TYPE_WIND: WIND_SET, TYPE_RENEWABLES: RENEWABLES_SET,
             TYPE_STORAGE: STORAGE_SET}
GEN_LIST = [COL_EXPORT, COL_IMPORT, TYPE_COAL, COL_DIESEL, COL_OIL, TYPE_GAS,
            COL_NUCLEAR, COL_BIOMASS, TYPE_RENEWABLES, TYPE_STORAGE]
BASIC_LIST = [COL_TIMESTAMP, COL_PRICE]   #~todo~ add temperature here?
LIMIT_LIST = [COL_TEMP, COL_BATT_CHG, COL_PUMPHYDRO_CHG]

priceUnit = '$/MWh'
genUnit = 'MW'
timeUnit = 5   #in minutes
tempUnit = '°C'
emissionsUnit = 'gCO₂/kWh'
dateFormat = '%Y-%m-%d %H:%M'
titleTemplate = '{2} ~ {0:%A} {0:%b} {0:%-d}, {0:%Y} to ' \
                '{1:%A} {1:%b} {1:%-d}, {1:%Y}'
#https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior

# colour palette
colourPalette = { COL_EXPORT: 'grey40', COL_IMPORT: 'purple3',
    COL_HYDRO: 'cornflowerblue', COL_NUCLEAR: 'red', COL_BIOMASS: 'hotpink2',
    TYPE_WIND: 'springgreen4', COL_WIND_ON: 'forestgreen',
    COL_WIND_OFF: 'seagreen', TYPE_RENEWABLES: 'yellowgreen',
    TYPE_SOLAR: 'darkgoldenrod1', COL_SOLAR_THERMAL: 'goldenrod3',
    COL_SOLAR_ROOF: 'gold2', COL_SOLAR_UTIL: 'goldenrod1',
    COL_GEOTHERM: 'burlywood', COL_OIL: 'slategray',
    COL_DIESEL: 'firebrick', TYPE_GAS: 'tomato', COL_GAS_CCGT: 'tomato3',
    COL_GAS_STEAM: 'sandybrown', COL_GAS_REP: 'lightsteelblue',
    COL_GAS_OCGT: 'wheat2', TYPE_COAL: 'sienna', COL_COAL_BROWN: 'brown',
    COL_COAL_BLACK: 'black', TYPE_STORAGE: 'skyblue', COL_BATT_CHG: 'orchid',
    COL_BATT_DIS: 'dodgerblue3', COL_PUMPHYDRO_CHG: 'turquoise',
    COL_PUMPHYDRO_DIS: 'deepskyblue' }

# CO₂ intensity (in gCO₂/kWh)
cohtoo = { COL_IMPORT: 200, COL_HYDRO: 24, TYPE_RENEWABLES: 0, COL_NUCLEAR: 12,
    TYPE_WIND: 11, COL_WIND_ON: 11, COL_WIND_OFF: 12, TYPE_SOLAR: 45,
    COL_SOLAR_ROOF: 45, COL_SOLAR_UTIL: 45, COL_SOLAR_THERMAL: 27,
    COL_GEOTHERM: 38, COL_OIL: 650,
    TYPE_GAS: 490, COL_GAS_CCGT: 410, COL_GAS_OCGT: 780, COL_GAS_STEAM: 560,
    COL_GAS_REP: 750, COL_DIESEL: 1130, COL_BIOMASS: 230,
    TYPE_COAL: 820, COL_COAL_BROWN: 1290, COL_COAL_BLACK: 890,
    TYPE_STORAGE: 0, COL_BATT_DIS: 0, COL_PUMPHYDRO_DIS: 0 }

config = configparser.ConfigParser(interpolation=None, delimiters=(':'))
config.optionxform = str   #preserve case

def load_config(source):
    global titleTemplate
    #clear any existing config data (except default section)
    config.clear()
    #now read data
    config.read_file(open(source))
    #note https://docs.python.org/3/library/configparser.html#configparser.ConfigParser.read
    #will cumulatively load several config files...
    #~todo~ investigate possibilities here
    # also, set up template for plot title
    gencfg = config['general']
    if 'title' in gencfg:
        matchObj = re.match(r'(.*?)(%.+%.+)\b(.*)', gencfg['title'])
        if matchObj == None:
            titleTemplate = gencfg['title']
        else:
            titleTemplate = matchObj.group(1)
            rawstring = matchObj.group(2)
            titleTemplate += re.sub(r'(%.+?\w{0,1})\b', r'{0:\1}', rawstring) \
                  + " to " + re.sub(r'(%.+?\w{0,1})\b', r'{1:\1}', rawstring) \
                  + matchObj.group(3)
    return config

def read_config(source):
    xtraconfig = configparser.ConfigParser()
    xtraconfig.optionxform = str
    xtraconfig.read_file(open(source))
    return xtraconfig

def title(startdate, enddate, fallback='"it\'s a trap"'):
    return titleTemplate.format(startdate, enddate, fallback)

def nicetype(rawstring, template='~', capitalise=False):
    #template selection + allow custom definition
    templates = {'~': '{}~{}', '()': '{} ({})', 'nl': '{}\n({})'}
    if template in templates:
        casting = templates[template]
    else:
        casting = template
    #~todo~ implement capitalisation option
    #first handle adjusted or out-of-state labels
    matchObj = re.match(r'(.*)_(.*)', rawstring)
    if matchObj != None:
        rawstring = '{} ({})'.format(matchObj.group(1), matchObj.group(2))
    matchObj = re.match(r'(.*)[,\.](.*)', rawstring)
    if matchObj == None:
        return rawstring
    else:
        return casting.format(matchObj.group(1), matchObj.group(2))

def getBool(hashdata={}, keydata=None, section=None, default=False):
    if hashdata:
        data = hashdata.get(keydata)
    else:   #use config data
        data = config[section].get(keydata, None)
    if data is None:
        return default
    elif isinstance(data, bool):
        return data
    return data.lower() in ('true', 'yes', 'on', 't', '1')

def flatish(filterlist, sourcelist=GEN_LIST, keepStructure=False,
            inverse=False):
    for item in sourcelist:
        if item in GROUPINGS:
            if keepStructure:
                #return as a tuple
                subtup = tuple(i for i in flatish(filterlist, GROUPINGS[item],
                                                  True, inverse))
                if len(subtup) == 1:
                    yield subtup[0]   #drop the structure
                elif len(subtup) > 1:
                    yield tuple((item, subtup))
                elif item in filterlist:   #& len(subtup) == 0
                    yield item   #return gen type on its own
            elif item in filterlist:
                yield item
            else:
                for subitem in flatish(filterlist, GROUPINGS[item], False,
                                       inverse):
                    yield subitem
        elif inverse:
            if item not in filterlist:
                yield item
        elif item in filterlist:
            yield item

def fullist(generators):
    full = BASIC_LIST[:]   #use copy
    if generators:
        full.extend(generators)
    else:
        full.extend(GEN_LIST)
    return full

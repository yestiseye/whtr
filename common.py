import os
from constants import load_config
from dataproc import gen_command, range_selected, loaddata


cache = "__pycache__"
configFile = ".whtr"

class Node(object):
    def __init__(self, title, parent=None):
        self.title = title
        if parent:
            parent.children.append(self)
        self.parent = parent
        self.children = []
        self.preamble = " - welcome to whtr -"

    def header(self):
        if self.preamble:
            print(self.preamble)

    def execute(self):
        return self

    def onexit(self):
        pass

    def active(self):
        return True

    def get_children(self):
        if not self.children:
            self.fill_children()
        return self.children

    def fill_children(self):
        pass

class DirNode(Node):
    def __init__(self, newdir, filelist, parent):
        Node.__init__(self, newdir[2:], parent)
        self.newdir = newdir
        self.filelist = filelist
        self.firstRun = True

    def execute(self):   #~todo~ should this only run on a first pass?
        if self.firstRun:
            self.parent.preamble = " --- whtr ---"
            #~todo~ could add test for above on node type to allow nested
            #directories
            os.chdir(self.newdir)
            print("now in dir:", os.getcwd())
            self.firstRun = False
        else:
            self.preamble = range_selected()   #~todo~ redundant?
            #~todo~ could potentially check for updated filelist
        return self

    def onexit(self):
        os.chdir("..")
        firstRun = True   #reset
        #~todo~ probably should clear all dataframes, etc here too

    def fill_children(self):
        if configFile in self.filelist:
            cfg = load_config(configFile)
        else:
            print("no config")   #~todo~ how to handle no config?
        # populate standard options
        #test for existing data & set date info for preamble
        existingData = cfg['general'].get('dbname', "whtr.csv")
        if existingData in self.filelist:
            self.filelist.remove(existingData)
            loaddata(existingData)
        # 1) basic statistics
        gen_command("basic", self, create_cmdnode)
        self.preamble = range_selected()
        #detect if unprocessed data present (& leave in filelist)
        self.filelist[:] = [x for x in sorted(self.filelist)
                              if x.endswith(cfg['general']['filetype'])]
        previousData = dict(cfg['data.processed'])
        if 'files' in previousData:
            prevFiles = previousData.get('files').split(",")
            self.filelist[:] = [x for x in self.filelist if x not in prevFiles]
        #~todo~ don't forget to write to disk once these files are processed
        if self.filelist:
            #add the actual command
            # 2) load new data into dataframe
            procnode = gen_command("procdata", self, create_cmdnode)
            procnode.customdata = self.filelist
            self.preamble +="\n{} datafile{} available for processing.".format(
                        len(self.filelist), ('s', '')[len(self.filelist) == 1])
        # 3) date range selection
        gen_command("daterange", self, create_cmdnode)
        # 4) time profile
        gen_command("timeplot", self, create_cmdnode)
        # 5) load duration curve
        #~todo~ this code is a mess, leave it out for now
#        gen_command("ldc", self, create_cmdnode)
        # 6) boxplots
        gen_command("boxplot", self, create_cmdnode)
        # X) populate customised command set
        cmdset = sorted([s for s in cfg.sections()
                        if s.startswith("cmd.customised")])
        cmdict = {s:dict(cfg.items(s)) for s in cmdset}
        for s in cmdset:
            customcmd = cmdict[s]
            cmdnode = gen_command(customcmd['type'], self, create_cmdnode,
                                  customcmd['descriptor'])
            #override the customdata array
            cmdnode.customdata = customcmd

class CmdNode(Node):
    def __init__(self, title, parent, status=None, *cmdlist):
        Node.__init__(self, title, parent)
        self.checkactive = status
        self.actionlist = cmdlist
        self.customdata = []

    def execute(self):
        for act in self.actionlist:
            if self.customdata:
                act(self.customdata)
                break   #assume only a single command
            else:
                act()
        self.parent.preamble = range_selected()
        return self.parent

    def active(self):
        if self.checkactive:
            return self.checkactive()
        else:
            return True

# do this to bypass the whole import of class imbroglio
def create_cmdnode(title, parent, status=None, *cmdlist):
    return CmdNode(title, parent, status, *cmdlist)

def load_root_node():
    root_node = Node("whtroot")   #the aqueduct, sanitation, and roads
    root_node.preamble += "\ncurrent dir: " + os.getcwd()
    firstSublevel = False
    for dirName, subdirs, files in os.walk("."):
        if firstSublevel:
            subdirs.clear()   #don't go beyond first subdirectory level
            DirNode(dirName, files[:], root_node)
        else:
            if cache in subdirs:
                subdirs.remove(cache)   #whtr code in base directory
            firstSublevel = True
    return root_node

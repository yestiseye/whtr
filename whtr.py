#!/usr/bin/env python3
#~todo~ make sure on upgrade that subdirectories are not overwritten or deleted

from common import load_root_node


def select(options, allowMulti=False):
    selectMap = {}
    for i, (descriptor, opt) in enumerate(options):
        #~todo~ colour code this for active state
        print("{:3d}{} {}".format(i+1, (']', '}')[opt.active()], descriptor))
        selectMap[i+1] = opt
    print("  0} Back")
    while True:
        try:
            values = list(map(int, input("...select > ").split()))
            if len(values) == 0:
                continue
            if 0 in values:
                return
            values = [selectMap[value] for value in values
                                       if value in selectMap]
            #~todo~ if multi, need to check prerequisites satisfied
            if allowMulti:
                return values
            elif len(values) == 1:
                if values[0].active():
                    return values[0]
                else:   #~todo~ maybe clear & re-print screen?
                    print("Inactive option, please select other")
                    continue
        except (ValueError, IndexError):
            print("Invalid input, please try again")



def main():
    # start by loading default config data (or use __init__.py?)
    #~todo~ do this
    #~todo~ also, detect when not already in whtr directory (use global config
    #file to set this location?)

    # initial menu options
    node = load_root_node()

    while True:
        options = []   #potentially multi-select
        # carry out selected (single) command if executable
        node = node.execute()
        for n in node.get_children():
            options.append((n.title, n))
        node.header()
        result = select(options)
        if result is None:
            if node.parent is None:
                break
            else:
                node.onexit()
                node = node.parent
        #~todo~ test here if result is array & sequentially execute options?
        else:
            node = result

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")


# whtr
> "Use the load duration curve Luke"

#### right, let's just dive in ok?
<sub><sup>*(These are the steps required on a [stable Debian o/s: currently "Stretch"](https://wiki.debian.org/DebianStable), & thus generally any other linux variant.  Given that particular o/s deliberately stays 2 or 3 steps behind the bleeding edge, other non-linux systems should not have a problem other than weird quirks …yes, looking at you Windows)*</sup></sub>

In a command line terminal, navigate to the location you want to [install]((https://git-scm.com/docs/git-clone)) &

```git clone git://github.com/yestiseye/whtr```

With the code now installed on your system, change into the new whtr directory &

```./whtr.py```https://git-scm.com/book/en/v2/Getting-Started-The-Command-Line

<sub><sup>*(anyone more familiar with git & python will have their own flavours on doing the same, but for those new to this, above is the easiest way to get up & running)*</sup></sub>

And you are up & running.  This clearly is useful only to linux users, so for the rest of you my recommendation is [install git](https://gist.github.com/derhuerst/1b15ff4652a867391f03) and then use the [relevant equivalent steps](https://git-scm.com/book/en/v2/Getting-Started-The-Command-Line) for your o/s.
obviously you'll need to have the prerequistes installed for it to actually work, and these are listed below with the relevant Debian packages as well.  Stuff is going to go wrong, especially on other o/ses, but that's why β-testing was invented :wink:  Log it as an issue; use the β-testing tag.

Python 3
R
rpy2

So a first, fairly limited functionality, version of the code.  The Load Duration Curve method is currently deactivated (because it is a mess right now... look if you dare).  Given this is half the reason whtr exists, this situation won't remain so for very long... ;-)  The other half of the reason, Simulated Scenarios, isn't even in the code yet. :-(
But the bare bones is there.

For anyone new to this kind of thing, your best bet is to navigate to the folder you download this to & try: ./whtr.py
Good luck (that's what works in a linux environment... not sure how Windows installs do it)

Also, tested on a Debian stable machine.  So other operating systems could easily have issues.  Runs off Python3 (& pandas), with rpy2 and obviously R.
More details to follow soon...

### So what is whtr?
A toolset to help make clear & unambiguous information about electricity market data easy to generate.  The basic design is to setup one or more subdirectories containing this data in raw form, and an easily configurable file (.whtr) to drive a menu of options that generate the required diagrams capturing the essential information in the data. These diagrams are:
 * Load Duration Curves - the primary tool, about as complete an illustration of the data as a single plot can be
 * Correlation plots - both within the current subdirectory, & between subdirectories
 * Boxplots - for a simple view on the distribution of generation types
 * Timeseries - time plot of generation output with configurable display options
 * CO₂ intensity plots - transformation of the time plot so that its CO₂ emissions can be viewed

It is this final diagram that is the whole point in the end.  Climate change is real.  The carbon emissions of the electricity sector and obtaining deep decarbonisation results is critical in averting truly dire consequences.  Without it, all other efforts lose any real meaning.  And the wider public has become increasingly aware of this, especially on #EnergyTwitter.  So now that public need to be properly informed, so that they can make wise decisions.
This is where the Load Duration Curve comes in.

### No… whtr?
Indeed.

Pro-tip(s):
 * on first usage the .whtr config file will (likely) be overwritten, thus losing any of the commented out configurations. Make a copy.

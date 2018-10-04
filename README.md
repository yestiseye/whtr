# whtr
> "Use the load duration curve Luke"

So a first, fairly limited functionality, version of the code.  The Load Duration Curve method is currently deactivated (because it is a mess right now... look if you dare).  Given this is half the reason whtr exists, this situation won't remain so for very long... ;-)  The other half of the reason, Simulated Scenarios, isn't even in the code yet. :-(
But the bare bones is there.

For anyone new to this kind of thing, your best bet is to navigate to the folder you download this to & try: ./whtr.py
Good luck (that's what works in a linux environment... not sure how Windows installs do it)

Also, tested on a Debian stable machine.  So other operating systems could easily have issues.  Runs off Python3 (& pandas), with rpy2 and obviously R.
More details to follow soon...

### So what is whtr?
A toolset to help make clear & unambiguous information about electricity market data easy to generate.  The basic design is to setup one or more subdirectories containing this data in raw form, and an easily configurable file (.whtr) to drive a menu of options that generate the required diagrams capturing the essential information in the data. These diagrams are:
 * Load Duration Curves - the primary tool, about as complete a description as a single plot can be
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

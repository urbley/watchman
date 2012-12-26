watchman
========

Customiseable process monitoring python script to check for running processes in linux and restart the failed 
process.

I realise at this point that this will only work for certain scenarios like mine where the start command to
restart the failed process is the same as the command you are searching for e.g.

I am searching for a specific process of "searchd --config /sphinx/conf/test.conf" and if not found the command to
restart this process is also "searchd --config /sphinx/conf/test.conf".

I've been thinking about ways to get around this to make the script more useful for other users and it seems the
easiest way to do this is to add it onto the end of the search reference in the conf. Something like;

Search1=searchd --conf test.conf::searchd test.conf --start i.e. [searchName]=[searchPattern]::[restartCommand]

I could then split on the :: or something just as obscure.

That's all well and good but once I get on top of the search/restart parameters I am going to have to consider how
to check for specific failed processes based on their stdout return.  Working with Sphinx I was quite lucky in that
every failed attempt had a specific "FATAL" string in the stdout which I could base the pass/fail on.

I'm not sure how to approach this from a generic point of view.  Maybe using pid files or similar would be a way
to approach this.

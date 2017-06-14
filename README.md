This is a simple perf timer that provides output in text and HTML format. It's very simple to work with.

When collection is turned on, the perf timer uses collections.deque for atomic insertion of events with no locking. When disabled, it does nothing at all.

To enable:

    perf_timer.EnablePerfTracking()
	
To disable:

    perf_timer.EnablePerfTracking(False)
	
Once enabled, you can create perf timers as context managers:

    with perf_timer.PerfTimer("BlockName"):
	    # Your code here
		
It will collect nested metrics on your application, recording the total time and callstacks for each block you instrument this way.

When you're finished, to print the report:

    perf_timer.PerfTimer.PrintPerfReport(perf_timer.ReportMode.HTML)
	
In addition to HTML (which will create an interactive html file with all the results), you can also use ReportMode.TREE and ReportMode.FLAT to print out an ascii table with the results.

When the report mode is HTML, the second parameter is a string indicating the output file name. It will default to <main_file_name>_PERF.html.

When the report mode is TREE or FLAT, the second parameter is a function that accepts strings to print. It defaults to 'print()'.
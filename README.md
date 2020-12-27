This is a simple perf timer that provides output in text and HTML format. It's very simple to work with.

The frame profiler supports a number of output modes, but the most useful is the HTML output mode, which offers multiple ways of viewing your data:

At the top of each page, you'll see a tree map view:

![Tree Map Example](doc_images/treemap_view.png?raw=true "Tree Map")

Below that, you'll see an expandable and collapsible table that can be configured in either a top-down tree view to see what call stacks are the most expensive:

![Tree View Example](doc_images/tree_view.png?raw=true "Tree View Example")

Or in a flat view to see which functions are taking the longest in all contexts combined:

![Flat View Example](doc_images/flat_view.png?raw=true "Flat View Example")

In a multithreaded environment, these outputs are presented per-thread, so you can see each thread's individual hotpoints, and they're also collected at the bottom of the page to show cumulative hotspots across all threads.

In addition to the HTML output view, there's also two text output modes (TREE and FLAT), which display the same tables you see in the HTML output as ASCII tables.

# Using perf_timer as a library

## Basic Usage

When collection is turned on, the perf timer uses collections.deque for atomic insertion of events with no locking. When disabled, it does nothing at all.

To enable:

    perf_timer.EnablePerfTracking()
	
To disable:

```python
import perf_timer
perf_timer.EnablePerfTracking(False)
```
	
Once enabled, you can create perf timers as context managers:

```python
import perf_timer
with perf_timer.PerfTimer("BlockName"):
    # Your code here
```
		
It will collect nested metrics on your application, recording the total time and callstacks for each block you instrument this way.

When you're finished, to print the report:

```python
import perf_timer
perf_timer.PerfTimer.PrintPerfReport(perf_timer.ReportMode.HTML)
```

In addition to HTML (which will create an interactive html file with all the results), you can also use ReportMode.TREE and ReportMode.FLAT to print out an ascii table with the results.

When the report mode is HTML, the second parameter is a string indicating the output file name. It will default to <main_file_name>_PERF.html.

When the report mode is TREE or FLAT, the second parameter is a function that accepts strings to print. It defaults to 'print()'.

## Frame-based Profiling

PerfTimer also supports frame-based profiling. The term "frame-based" here is derived from the use case of profiling video games, where hitches and long frames can be very difficult to profile. However, the implementation is generic enough that it can be used for capturing profile reports in any context where you want to do any kind of grouping of profile results.

To use frame-based profiling, simply add a numerical current frame count to your PerfTimer constructor:

```python
import perf_timer
global frameCount
with perf_timer.PerfTimer("BlockName", frameCount):
    # Your profiled code here
```

In the HTML output mode, this will add a frame-by-frame performance graph to the top of the HTML page. Initially, the profile output will show the collected data from all frames together, but clicking on any of these bars will load the profiling data for that specific frame below it, allowing for inspection of hotspots within the longest frames and hitches.

![Frame Report Example](doc_images/frame_header.png?raw=true "Frame Report Example")

If you're profiling a large number of frames and having difficulty clicking on the frame you want, you can also click and drag within the header to zoom in on a segment of the output so that you can click on the one you want more easily.

#### !! A word of warning !!

Running the frame-based profiler with output modes of FLAT or TREE will generate a separate ascii table PER FRAME and PER THREAD. This could result in an extremely large amount of output. It's *strongly* recommended to use frame-based profiling only with the HTML output mode.

# Using perf_timer as an external viewer

In addition to being usable as a python library, perf_timer can also be used to generate visualization output for metrics collected from other applications, potentially written in different languages. If you can generate metrics in the format required by perf_timer, it can consume those and convert them into output. There are two formats supported by perf_timer: a JSON format or a binary format.

Both standard and frame-based profiling modes are supported in the external viewer mode. See the section on frame-based profiling above for more information on this.

## JSON format

The JSON format is relatively simple. It contains an array of arrays, with each nested array representing a single recorded metric. The format of the array is as follows:

```
[
    // Either 0 (ENTER CONTEXT) or 1 (EXIT CONTEXT)
    operation: number,

    // Unique number per thread. Doesn't matter what it is as long as it's unique.
    threadId: number, 

    // Current frame count. If you don't wish to use frame-based profiling, set this to -1.
    frameId: number, 

    // Timestamp of the event, in nanoseconds - this is an absolute time, not a duration
    timestamp: number,

    // The string name for the current block. Parent block names should not be included. 
    blockName: string 
]
```

Example JSON data:

```json
[
  [0, 1, 0, 1609044830711675392, "DemoFunc_0"],
  [0, 1, 0, 1609044830713163520, "DemoFunc_0_0"],
  [0, 1, 0, 1609044830714651392, "DemoFunc_1_0"],
  [1, 1, 0, 1609044830716141056, "DemoFunc_1_0"],
  [1, 1, 0, 1609044830716141056, "DemoFunc_0_0"],
  [0, 1, 0, 1609044830716141056, "DemoFunc_0_1"],
  [0, 1, 0, 1609044830717628672, "DemoFunc_1_0"],
  [1, 1, 0, 1609044830719115520, "DemoFunc_1_0"],
  [1, 1, 0, 1609044830719115520, "DemoFunc_0_1"],
  [1, 1, 0, 1609044830719115520, "DemoFunc_0"],
  [0, 1, 1, 1609044830719115520, "DemoFunc_0"],
  [1, 1, 1, 1609044830720603392, "DemoFunc_0"]
]
```

Note that it is the responsibility of the application to ensure all ENTER events are balanced with a corresponding EXIT event and that the events are ordered correctly within their thread. (Cross-thread ordering does not matter - thread events can be interleaved, or each thread can have its own section of the array.) `perf_timer` will use the ordering of the ENTER and EXIT events to build call stacks for the tree views.

## Binary format

The binary format is similar to the JSON format, but, perhaps expectedly, is more strict. It's provided to allow for native applications to generate the output more efficiently.

**Note that the binary format does not include ANY alignment padding to ensure it will work across all languages and architectures without making any assumptions about the alignment of data. Structs used to generate the metrics file should thus be packed. All values should also be provided in little endian byte order, meaning if you generate the file on a big endian system, you will need to convert your values.**

The overall file format is as follows:

| Field | Type | Size | Values |
|-------|------|------|--------|
| Magic | unsigned int32 |4 bytes | MUST contain the value 0xFA57 |
| Count | unsigned int32 | 4 bytes | The total number of events recorded |
| Events | struct Event | (see struct definition) | |

The definition of `struct Event` is as follows:

| Field | Type | Size | Values |
|-------|------|------|--------|
| Operation | Byte | 1 byte | 0 (START_CONTEXT) or 1 (END_CONTEXT) |
| Thread ID | unsigned int64 | 8 bytes | Any integer value unique to the current thread
| Frame ID | signed int32 | 4 bytes | The current frame count for this event, or -1 if not using frame-based profiling |
| Timestamp | unsigned int64 | 8 bytes | The timestamp of the event in nanoseconds |
| Block Name | char* | Variable | The name of the current context as a null-terminated string

Example binary data:

![Binary Data Example](doc_images/binary_example.png?raw=true "Binary Data Example")

# Samples

The `samples` directory in the tree includes some randomly-generated examples of the HTML output, as well as example binary and json files containing example data.

If you use the 010 editor by SweetScape, the example data can be viewed using the following template definition (as shown in the screenshot above):

```
int magic <format=hex, comment="Must be 0xFA57">;
Assert(magic == 0xFA57);
int count<comment="Number of events">;

enum<byte> Operation
{
    Start = 0,
    End = 1,
};

local int i;
for( i = 0; i < count; i++ )
{
    struct Foo
    {
        Operation op<comment="Event operation">;
        int64 threadId<comment="Numeric thread ID">;
        int32 frameId<comment="Frame counter for this event">;
        uint64 time<comment="Nanosecond timestamp">;
        string name<comment="Null-terminated block name">;
    };
    Foo f;
}

```

You can also use that template to test the validity of any binary output you generate.

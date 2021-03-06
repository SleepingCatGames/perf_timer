# Copyright (C) 2016 Jaedyn K. Draper
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
.. module:: perf_timer
	:synopsis: Thread-safe performance timer to collect high-level performance statistics

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import time
import threading
import re
import math
import sys
import os

from collections import deque
_collecting = True

class ReportMode(object):
	"""
	Enum defining the perf timer reporting mode.
	"""
	TREE = 0
	FLAT = 1
	HTML = 2

def EnablePerfTracking(enable=True):
	"""
	Enable (or disable) the perf timer.

	:param enable: True to enable the perf timer, False to disable.
	:type enable: bool
	"""
	global _collecting
	_collecting = enable

def DisablePerfTracking():
	"""
	Helper function for explicitly disabling the perf timer.
	"""
	EnablePerfTracking(False)

_htmlHeader = """<!DOCTYPE html><HTML>
	<HEAD>
		<title>Perf report for {0}</title>
		<script type="text/javascript">
			var scriptLoaded = false;
			function checkScriptLoaded() {{
				if (!scriptLoaded) {{
					document.getElementById("errorbar").innerHTML="Could not contact gstatic.com to access google charts API.Tree maps will not be available until connection is restored.";
				}}
			}}
			function _width(s, w) {{
				s = "0000" + s
				return s.substring(s.length - w)
			}}
			function numberWithCommas(x) {{
				return x.toString().replace(/\B(?=(\d{{3}})+(?!\d))/g, ",");
			}}
			function _formatTime(totaltime, globaltotal){{
				msec = Math.floor(totaltime*1000);
				usec = Math.floor((totaltime - Math.floor(totaltime))*100000)
				ret = numberWithCommas(msec) + "." + _width(usec, 2)
				if(globaltotal !== undefined)
				{{
					ret += ' (' + Math.min(100,totaltime/globaltotal * 100).toFixed(2) + '%)'
				}}
				return ret;
			}}
		</script>
		<style>
			.hoversort {{
			 	cursor: pointer; cursor: hand;
			}}
			.hoversort:hover{{
				color:blue;
			}}
			.percentbar {{
				height:22px;
				background-color:#a060ff;
				margin-top:-22px;

			}}

			.gradient {{
				background: rgba(235,233,249,1);
				background: -moz-linear-gradient(top, rgba(235,233,249,1) 0%, rgba(216,208,239,1) 50%, rgba(206,199,236,1) 51%, rgba(193,191,234,1) 100%);
				background: -webkit-gradient(left top, left bottom, color-stop(0%, rgba(235,233,249,1)), color-stop(50%, rgba(216,208,239,1)), color-stop(51%, rgba(206,199,236,1)), color-stop(100%, rgba(193,191,234,1)));
				background: -webkit-linear-gradient(top, rgba(235,233,249,1) 0%, rgba(216,208,239,1) 50%, rgba(206,199,236,1) 51%, rgba(193,191,234,1) 100%);
				background: -o-linear-gradient(top, rgba(235,233,249,1) 0%, rgba(216,208,239,1) 50%, rgba(206,199,236,1) 51%, rgba(193,191,234,1) 100%);
				background: -ms-linear-gradient(top, rgba(235,233,249,1) 0%, rgba(216,208,239,1) 50%, rgba(206,199,236,1) 51%, rgba(193,191,234,1) 100%);
				background: linear-gradient(to bottom, rgba(235,233,249,1) 0%, rgba(216,208,239,1) 50%, rgba(206,199,236,1) 51%, rgba(193,191,234,1) 100%);
				filter: progid:DXImageTransform.Microsoft.gradient( startColorstr='#ebe9f9', endColorstr='#c1bfea', GradientType=0 );
			}}
		</style>
	</HEAD>
	<BODY onload="checkScriptLoaded()">
		<div id="errorbar" style="background-color:#ff0000"></div>
		<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js" onload="scriptLoaded=true;" ></script>
		<h1>Perf Report: <i>{0} {1}</i></h1>
"""

_blocks = [
"""		<div style="margin:2px 10px;padding: 5px 10px;background-color:lavender;border: 1px solid grey;">
			<h3>{1}</h3>

			<div id="chart_div_{0}"></div>
			<script type="text/javascript">
				google.charts.load("current", {{"packages":["treemap"]}});
				google.charts.setOnLoadCallback(drawChart);
				function drawChart() {{
					var data = new google.visualization.DataTable();
					data.addColumn("string", "ID");
					data.addColumn("string", "Parent");
					data.addColumn("number", "Exclusive time in milliseconds");
					data.addColumn("number", "Inclusive time in milliseconds");
					data.addRows([
""",
"""					]);
					var tree = new google.visualization.TreeMap(document.getElementById("chart_div_{0}"));
					function showFullTooltip(row, size, value) {{
						return '<div style="background:#fd9; padding:10px; border-style:solid">' +
						'<span style="font-family:Courier"><b>' +
						data.getValue(row, 0).split("\x0b").join("").split("<").join("&lt;").split(">").join("&gt;")
						+ ':</b>' + _formatTime(data.getValue(row, 2)) + ' ms</span></div>'
					}}
					var options = {{
						highlightOnMouseOver: true,
						maxDepth: 1,
						maxPostDepth: 20,
						minHighlightColor: "#80a0ff",
						midHighlightColor: "#ffffff",
						maxHighlightColor: "#ff0000",
						minColor: "#7390E6",
						midColor: "#E6E6E6",
						maxColor: "#e60000",
						headerHeight: 15,
						showScale: false,
						height: 500,
						useWeightedAverageForAggregation: true,
						generateTooltip: showFullTooltip
					}};
					tree.draw(data, options);
				}}
			</script>
			<script type="text/javascript">
				var datas_{0} = [
""",
"""				function HideChildren_{0}(parentId) {{
						className = '{0}_Parent_' + parentId
						elems = document.getElementsByClassName(className)
						arrowElem = document.getElementById("arrow_{0}_"+parentId)
						for(var i = 0; i < elems.length; ++i) {{
							var elem = elems[i]
							if(elem.style.maxHeight == '0px') {{
								elem.style.maxHeight=elem.rememberMaxHeight
								arrowElem.innerHTML = '&#x25bc;'
							}}
							else
							{{
								elem.style.maxHeight='0px'
								arrowElem.innerHTML = '&#x25b6;'
							}}
						}}
					}}

					var mode_{0} = "tree"

					function Flatten_{0}() {{
						ret = {{}}
						function recurse(datas) {{
							if(datas.length == 0) {{
								return;
							}}
							for(var i = 0; i < datas.length; ++i) {{
								if(datas[i][0] in ret) {{
									item = ret[datas[i][0]]
									item[0] += datas[i][1]
									item[1] += datas[i][2]
									item[2] += datas[i][3]
									item[3] += datas[i][4]
									item[4] += datas[i][5]
									item[5] += datas[i][6]
									item[6] += datas[i][7]
									item[7] += datas[i][8]
									item[8] += datas[i][9]
								}}
								else {{
									ret[datas[i][0]] = [
										datas[i][1],
										datas[i][2],
										datas[i][3],
										datas[i][4],
										datas[i][5],
										datas[i][6],
										datas[i][7],
										datas[i][8],
										datas[i][9]
									];
								}}
								recurse(datas[i][10]);
							}}
						}}
						recurse(datas_{0});
						retArray = []
						for(var key in ret) {{
							item = ret[key]
							retArray.push([
								key,
								item[0],
								item[1],
								item[2],
								item[3],
								item[4],
								item[5],
								item[6],
								item[7],
								item[8],
								[]
							]);
						}}
						return retArray;
					}}
					
					function escapeHtml(unsafe) {{
						return unsafe
							 .replace(/&/g, "&amp;")
							 .replace(/</g, "&lt;")
							 .replace(/>/g, "&gt;")
							 .replace(/"/g, "&quot;")
							 .replace(/'/g, "&#039;");
					}}

					var prevSortKey_{0} = 1
					var prevSortType_{0} = -1
					var maxId_{0} = -1
					function Populate_{0}(sortKey) {{
						var sortType = 1
						if(sortKey == 0) {{
							sortType = -1
						}}
						if(prevSortKey_{0} == sortKey && prevSortType_{0} == sortType) {{
							sortType *= -1
						}}
						prevSortKey_{0} = sortKey
						prevSortType_{0} = sortType

						elem = document.getElementById("stack_{0}")
						bg1 = "#DFDFF2"
						bg2 = "#D3D3E6"
						var s = '<div style="border:1px solid black"><div style="font-weight:bold;border-bottom:1px solid black;" class="gradient">'
						s += '<span class="hoversort" style="width:37%;display:inline-block;text-align:center;" onclick="Populate_{0}(0)">Block</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(1)">Inclusive</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(2)">Exclusive</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(3)">Count</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(4)">Inclusive Max</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(5)">Inclusive Min</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(6)">Inclusive Mean</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(7)">Exclusive Max</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(8)">Exclusive Min</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(9)">Exclusive Mean</span>'
						s += '</div>'
						var id = 1
						function recurse(oneLevel, depth, parentId) {{
							oneLevel = oneLevel.sort(function(a, b) {{
								var x = a[sortKey]; var y = b[sortKey];
								return ((x < y) ? 1 : ((x > y) ? -1 : 0)) * sortType;
							}});
							for(var i=0; i < oneLevel.length; ++i) {{
								var thisId = id;
								id += 1;
								if(thisId %2 == 0) {{
									bg1 = "#C8C6F2"
									bg2 = "#B3B1D9"
								}}
								else {{
									bg1 = "#BDBBE6"
									bg2 = "#A8A7CC"
								}}
								s += '<div style="width:100%;overflow:hidden;transition:max-height 0.5s linear" class="{0}_Parent_'+parentId+'", id="{0}_'+thisId+'">'
								s += '<div style="line-height:22px;"><span style="height:100%;width:37%;display:inline-block;background-color:'+bg1+'" '
								if(oneLevel[i][10].length != 0) {{
									s += 'class="hoversort" onclick="HideChildren_{0}(\\''+thisId+'\\')"'
								}}
								s += '><span style="width:20px;display:inline-block;margin-left:' + (depth * 15) + 'px;" id="arrow_{0}_'+thisId+'">'
								if(oneLevel[i][10].length != 0) {{
									s += '&#x25bc;'
								}}
								s += '</span>' + escapeHtml(oneLevel[i][0]) + '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][1], totals_{0}[0])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][1]/totals_{0}[0] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg1+'">' + _formatTime(oneLevel[i][2], totals_{0}[0])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][2]/totals_{0}[0] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + oneLevel[i][3] + ' (' + Math.min(100,oneLevel[i][3]/totals_{0}[1] * 100).toFixed(2) + '%)'
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][3]/totals_{0}[1] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg1+'">' + _formatTime(oneLevel[i][4], totals_{0}[2])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][4]/totals_{0}[2] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][5], totals_{0}[3])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][5]/totals_{0}[3] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][6], totals_{0}[4])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][6]/totals_{0}[4] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][7], totals_{0}[5])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][7]/totals_{0}[5] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][8], totals_{0}[6])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][8]/totals_{0}[6] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][9], totals_{0}[7])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][9]/totals_{0}[7] * 100) + '%;"></div>'
								s += '</span></div>'
								recurse(oneLevel[i][10], depth + 1, thisId)
								s += "</div>"
							}}
						}}
						var datas;
						if(mode_{0} == "flat") {{
							datas = Flatten_{0}();
						}}
						else {{
							datas = datas_{0};
						}}
						recurse(datas, 0, 0)
						s += '</div>'
						s += '{2}'
						elem.innerHTML = s
						for(var i = 0; i < id; ++i) {{
							className = '{0}_Parent_' + i
							elems = document.getElementsByClassName(className)
							for(var j = 0; j < elems.length; ++j) {{
								var elem = elems[j]
								elem.style.maxHeight = Math.max(22, elem.clientHeight) + "px"
								elem.rememberMaxHeight = elem.style.maxHeight
							}}
						}}
						maxId_{0} = id
					}}

					function ExpandAll_{0}() {{
						for(var i = 1; i < maxId_{0}; ++i) {{
							className = '{0}_Parent_' + i
							elems = document.getElementsByClassName(className)
							arrowElem = document.getElementById("arrow_{0}_"+i)
							for(var j = 0; j < elems.length; ++j) {{
								var elem = elems[j]
								elem.style.maxHeight=elem.rememberMaxHeight
								arrowElem.innerHTML = '&#x25bc;'
							}}
						}}
						return false;
					}}

					function CollapseAll_{0}() {{
						for(var i = 1; i < maxId_{0}; ++i) {{
							className = '{0}_Parent_' + i
							elems = document.getElementsByClassName(className)
							arrowElem = document.getElementById("arrow_{0}_"+i)
							for(var j = 0; j < elems.length; ++j) {{
								var elem = elems[j]
								elem.style.maxHeight='0px'
								arrowElem.innerHTML = '&#x25b6;'
							}}
						}}
						return false;
					}}

					function RenderTreeView_{0}() {{
						if(mode_{0} != "tree") {{
							mode_{0} = "tree";
							prevSortType_{0} *= -1
							Populate_{0}(prevSortKey_{0})
							elem = document.getElementById("expandcollapse_{0}")
							elem.style.opacity = 100
							elem.style.visibility = "visible"
						}}
						return false;
					}}

					function RenderFlatView_{0}() {{
						if(mode_{0} != "flat") {{
							mode_{0} = "flat";
							prevSortType_{0} *= -1
							Populate_{0}(prevSortKey_{0})
							elem = document.getElementById("expandcollapse_{0}")
							elem.style.opacity = 0
							elem.style.visibility = "hidden"
						}}
						return false;
					}}
			</script>
			<div>
			<div style="border:1px solid black;padding:0px 6px">
				<div style="float:left;transition:opacity 0.5s, visibility 0.5s" id="expandcollapse_{0}">
					<a href="javascript:;" onclick="ExpandAll_{0}()">expand all</a> |
					<a href="javascript:;" onclick="CollapseAll_{0}()">collapse all</a>
				</div>
				&nbsp;
				<div style="float:right">
					View as:
					<a href="javascript:;" onclick="RenderTreeView_{0}()">tree</a> |
					<a href="javascript:;" onclick="RenderFlatView_{0}()">flat</a>
				</div>
			</div>
			<div style="clear:left" id="stack_{0}"></div>
			</div>
			<script type="text/javascript">
				Populate_{0}(1);
			</script>
		</div>
"""
]

_htmlFooter = """	</BODY>
</HTML>"""


def _formatTime(totaltime):
	msec = totaltime*1000
	return "{:.2f}".format(msec)

class PerfTimer(object):
	"""
	Performance timer to collect performance stats on csbuild to aid in diagnosing slow builds.
	Used as a context manager around a block of code, will store cumulative execution time for that block.

	:param blockName: The name of the block to store execution for.
	:type blockName: str
	:param frame: A frame counter for frame-based programs. If this is set, the HTML output mode
		will generate multiple pages, one for each frame, and a performance graph by frame.
	:type frame: int or None
	"""
	perfQueue = deque()
	annotations = deque()
	perfStack = threading.local()
	minFrameTime = None
	
	@staticmethod
	def setMinFrameTime(minTime):
		PerfTimer.minFrameTime = minTime

	def __init__(self, blockName, frame=None):
		if _collecting:
			self.frame = frame
			self.blockName = blockName
			self.incstart = 0
			self.excstart = 0
			self.exclusive = 0
			self.inclusive = 0
			self.scopeName = blockName
			self.threadId = threading.current_thread().ident

	def __enter__(self):
		if _collecting:
			now = time.time()
			try:
				prev = PerfTimer.perfStack.stack[-1]
				prev.exclusive += now - prev.excstart
				self.scopeName = prev.scopeName + "::" + self.blockName

				PerfTimer.perfStack.stack.append(self)
			except:
				PerfTimer.perfStack.stack = [self]

			self.incstart = now
			self.excstart = now
		return self

	def __exit__(self, excType, excVal, excTb):
		if _collecting:
			now = time.time()
			try:
				prev = PerfTimer.perfStack.stack[-2]
				prev.excstart = now
			except:
				pass

			self.exclusive += now - self.excstart
			self.inclusive = now - self.incstart

			PerfTimer.perfQueue.append((self.scopeName, self.inclusive, self.exclusive, self.threadId, self.frame, self.incstart, now))
			PerfTimer.perfStack.stack.pop()
			
	@staticmethod
	def Note(txt, frame=None):
		if _collecting:
			now = time.time()
			PerfTimer.annotations.append((txt, threading.current_thread().ident, frame, now))

	@staticmethod
	def PrintPerfReport(reportMode, output=None, name=None):
		"""
		Print out all the collected data from PerfTimers in a heirarchical tree

		:param reportMode: :class:`ReportMode` enum value defining how the report is output to the user.
		:type reportMode: int

		:param output: When the report mode is "flat" or "tree", this is a function that receives each line of output (defaults to stdout when None).
		               When the report mode is "html", this is the name of the file dumped by the report (defaults to the name of the main module file + "_PERF.html" when None).
		:type output: None or :class:`collections.Callable` or str
		
		:param name: The name of the application. Running in normal python mode, this will default to the name of the __main__ module. This only affects the header in HTML mode.
		:type name: None or str
		"""

		if name is None:
			name = os.path.basename(sys.modules["__main__"].__file__)

		if output is None:
			if reportMode != ReportMode.HTML:
				# pylint: disable=invalid-name,missing-docstring
				def printIt(*args, **kwargs):
					print(*args, **kwargs)

				output = printIt
			else:
				output = os.path.basename(os.path.splitext(name)[0] + "_PERF.html")

		elementsByFrame = {}
		earliestByFrame = {}
		latestByFrame = {}
		allFramesQueue = deque()
		allFramesAnnotations = deque()
		annotationsByFrame = {}
		while True:
			try:
				pair = PerfTimer.perfQueue.popleft()
				frame = pair[4]
				if frame in earliestByFrame:
					earliestByFrame[frame] = min(earliestByFrame[frame], pair[5])
					latestByFrame[frame] = max(latestByFrame[frame], pair[6])
				else:
					earliestByFrame[frame] = pair[5]
					latestByFrame[frame] = pair[6]
				if PerfTimer.minFrameTime is not None and (duration * 1000) < PerfTimer.minFrameTime:
					continue
				elementsByFrame.setdefault(frame, deque()).append(pair)
				annotationsByFrame[frame] = deque();
				allFramesQueue.append(pair)
			except IndexError:
				break

		while True:
			try:
				pair = PerfTimer.annotations.popleft()
				frame = pair[2]
				globalEarliest = min(earliestByFrame.values())
				allFramesPair = (pair[0], pair[1], pair[2], pair[3] - globalEarliest)
				allFramesAnnotations.append(allFramesPair)
				# Convert timestamp to a relative timestamp for this frame
				pair = (pair[0], pair[1], pair[2], pair[3] - earliestByFrame[frame])
				annotationsByFrame[frame].append(pair)
			except IndexError:
				break
				
		if len(elementsByFrame) > 1 and reportMode == ReportMode.HTML:
			if not os.path.exists(os.path.join(os.path.dirname(output), "frames")):
				os.mkdir(os.path.join(os.path.dirname(output), "frames"))
			if __name__ == "__main__":
				print("Generating combined frame output...")
			PerfTimer.perfQueue = allFramesQueue
			#PerfTimer.annotations = allFramesAnnotations
			thisOutput = os.path.join(os.path.dirname(output), "frames", "_ALL.".join(os.path.basename(output).rsplit(".", 1)))
			PerfTimer._printPerfReport(reportMode, thisOutput, None, name)

		for key in sorted(elementsByFrame.keys()):
			if key is not None:
				if reportMode != ReportMode.HTML:
					output("==============================")
					output("Frame #{}".format(key))
					output("==============================")
				elif __name__ == "__main__":
					sys.stdout.write("\rGenerating individual frame output for frame {}...".format(key))
			duration = latestByFrame[key] - earliestByFrame[key]
			PerfTimer.perfQueue = elementsByFrame[key]
			PerfTimer.annotations = annotationsByFrame[key]
			thisOutput = output
			if len(elementsByFrame) > 1 and reportMode == ReportMode.HTML:
				thisOutput = os.path.join(os.path.dirname(output), "frames", "_{}.".format(key).join(os.path.basename(output).rsplit(".", 1)))
			PerfTimer._printPerfReport(reportMode, thisOutput, key, name)

		if len(elementsByFrame) > 1 and reportMode == ReportMode.HTML:
			if __name__ == "__main__":
				print("\nGenerating index file and performance graph...")
			frameFile = os.path.join(os.path.dirname(output), "frames", "_${pn}.".join(os.path.basename(output).rsplit(".", 1))).replace("\\", "/")
			allFramesFile = os.path.join(os.path.dirname(output), "frames", "_ALL.".join(os.path.basename(output).rsplit(".", 1))).replace("\\", "/")
			html = """
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/1.44.1/plotly.js"></script>

<style>
html, body { height: 100%; }
.js-plotly-plot .plotly .cursor-ew-resize {
  cursor: crosshair;
}
#plot {
  height: 300px;
}
#frameData {
  width: 100%;
  border: none;
}
</style>
</head>
<body style="height:99%;">
  <div id="plot"></div>
  <iframe id="frameData" src=\"""" + allFramesFile + """\" style="height:calc(100% - 300px);">
  </iframe>
<script type="text/javascript">
const dataX = """ + str(list(sorted(elementsByFrame.keys()))) + """;
const dataY = """ + str([(latestByFrame[key] - earliestByFrame[key]) * 1000 for key in sorted(elementsByFrame.keys())]) + """;
const data = [
  {
    x: dataX,
    y: dataY,
    name: 'Performance',
    type: 'bar'
  },
]
const layout = {
  autosize: true,
  xaxis: {
    automargin: true,
    autorange: true,
    type: 'linear',
    title: { text: 'Frame' },
  },
  yaxis: {
    automargin: true,
    autorange: true,
    fixedrange: true,
    type: 'linear',
    title: { text: 'Time (ms)' },
  },
  legend: { x: 0, y: 1.2, bgcolor: '#E2E2E2' },
  title: {
    text: "Perf Report",
    x: 0.5,
    y: 1.1,
  },
}

const config = {
  editable: false,
  modeBarButtonsToRemove: ['sendDataToCloud'],
  displaylogo: false,
  locale: 'en-AU'
}

Plotly.newPlot(
  'plot',
  data,
  layout,
  config,
);

document.getElementById('plot').on('plotly_click', singleClickHandler);

function singleClickHandler(data) {
  let pn = data.points[0].pointNumber + 1;
  document.getElementById("frameData").src = `./""" + frameFile + """`;
  let tn = data.points[0].curveNumber;
  let colors = new Array(data.points[0].data.x.length).fill("#1f77b4")
  colors[pn-1] = '#C54C82';
  var update = {'marker':{color: colors, size:16}};
  Plotly.restyle('plot', update,[tn]);
}
</script>
</body>
</html>
"""
			with open(output, "w") as f:
				f.write(html)


	@staticmethod
	def _printPerfReport(reportMode, output, frameId, name):
		fullreport = {}
		threadreports = {}

		#pylint: disable=missing-docstring
		class Position(object):
			Inclusive = 0
			Exclusive = 1
			Count = 2
			MaxInc = 3
			MaxExc = 4
			MinInc = 5
			MinExc = 6

		while True:
			try:
				pair = PerfTimer.perfQueue.popleft()
				if reportMode == ReportMode.FLAT:
					split = pair[0].rsplit("::", 1)
					if len(split) == 2:
						key = split[1]
					else:
						key = split[0]
					pair = (
						key,
						pair[1],
						pair[2],
						pair[3]
					)

				fullreport.setdefault(pair[0], [0,0,0,0,0,999999999,999999999])
				fullreport[pair[0]][Position.Inclusive] += pair[1]
				fullreport[pair[0]][Position.Exclusive] += pair[2]
				fullreport[pair[0]][Position.Count] += 1
				fullreport[pair[0]][Position.MaxInc] = max(pair[1], fullreport[pair[0]][Position.MaxInc])
				fullreport[pair[0]][Position.MaxExc] = max(pair[2], fullreport[pair[0]][Position.MaxExc])
				fullreport[pair[0]][Position.MinInc] = min(pair[1], fullreport[pair[0]][Position.MinInc])
				fullreport[pair[0]][Position.MinExc] = min(pair[2], fullreport[pair[0]][Position.MinExc])

				threadreport = threadreports.setdefault(pair[3], {})
				threadreport.setdefault(pair[0], [0,0,0,0,0,999999999,999999999])
				threadreport[pair[0]][Position.Inclusive] += pair[1]
				threadreport[pair[0]][Position.Exclusive] += pair[2]
				threadreport[pair[0]][Position.Count] += 1
				threadreport[pair[0]][Position.MaxInc] = max(pair[1], threadreport[pair[0]][Position.MaxInc])
				threadreport[pair[0]][Position.MaxExc] = max(pair[2], threadreport[pair[0]][Position.MaxExc])
				threadreport[pair[0]][Position.MinInc] = min(pair[1], threadreport[pair[0]][Position.MinInc])
				threadreport[pair[0]][Position.MinExc] = min(pair[2], threadreport[pair[0]][Position.MinExc])
			except IndexError:
				break

		annotations = []
		while True:
			try:
				pair = PerfTimer.annotations.popleft()
			except IndexError:
				break
			else:
				annotations.append(pair)
				
		if not fullreport:
			return

		if reportMode == ReportMode.HTML:
			with open(output, "w") as f:
				#pylint: disable=missing-docstring
				class SharedLocals(object):
					identifiers = {}
					lastId = {}
					totalExc = 0
					totalCount = 0
					maxExcMean = 0
					maxIncMean = 0
					maxExcMax = 0
					maxExcMin = 0
					maxIncMax = 0
					maxIncMin = 0

				#pylint: disable=invalid-name
				def _getIdentifier(s):
					_,_,base = s.rpartition("::")
					if s not in SharedLocals.identifiers:
						SharedLocals.identifiers[s] = SharedLocals.lastId.setdefault(base, 0)
						SharedLocals.lastId[base] += 1
					return base + "\\x0b" * SharedLocals.identifiers[s]

				def _recurseHtml(report, sortedKeys, prefix, printed, itemfmt, indent):
					first = True
					for key in sortedKeys:
						if key in printed:
							continue

						if key.startswith(prefix):
							reportEntry = report[key]
							reportIncMean = reportEntry[Position.Inclusive] / reportEntry[Position.Count]
							reportExcMean = reportEntry[Position.Exclusive] / reportEntry[Position.Count]

							printkey = key.replace(prefix, "", 1)
							if printkey.find("::") != -1:
								continue
							if not first:
								f.write("\t" * (indent+1))
								f.write("],\n")
							f.write("\n")
							f.write("\t" * (indent+1))
							f.write(
								itemfmt.format(
									printkey,
									reportEntry[Position.Inclusive],
									reportEntry[Position.Exclusive],
									reportEntry[Position.Count],
									reportEntry[Position.MaxInc],
									reportEntry[Position.MinInc],
									reportIncMean,
									reportEntry[Position.MaxExc],
									reportEntry[Position.MinExc],
									reportExcMean,
								)
							)

							SharedLocals.totalExc += reportEntry[Position.Exclusive]
							SharedLocals.totalCount += reportEntry[Position.Count]
							SharedLocals.maxExcMean = max(SharedLocals.maxExcMean, reportExcMean)
							SharedLocals.maxIncMean = max(SharedLocals.maxIncMean, reportIncMean)
							SharedLocals.maxExcMax = max(SharedLocals.maxExcMax, reportEntry[Position.MaxExc])
							SharedLocals.maxIncMax = max(SharedLocals.maxIncMax, reportEntry[Position.MaxInc])
							SharedLocals.maxExcMin = max(SharedLocals.maxExcMin, reportEntry[Position.MinExc])
							SharedLocals.maxIncMin = max(SharedLocals.maxIncMin, reportEntry[Position.MinInc])

							f.write("\t" * (indent+2))
							f.write("[")
							printed.add(key)
							_recurseHtml(report, sortedKeys, key + "::", printed, itemfmt, indent + 2)
							first = False
					if not first:
						f.write("\t" * (indent+1))
						f.write("]\n")
						f.write("\t" * indent)
					f.write("]\n")

				def _printReportHtml(report, threadId, numericThreadId):
					if not report:
						return
					totalcount = 0
					for key in report:
						totalcount += report[key][Position.Count]

					sortedKeys = sorted(report, reverse=True, key=lambda x: report[x][0] if reportMode == ReportMode.TREE else report[x][1])

					threadScriptId = threadId.replace(" ", "_")
					f.write(_blocks[0].format(threadScriptId, threadId))

					f.write("\t\t\t\t\t\t['<{}_root>', null, 0, 0 ],\n".format(threadScriptId))
					for key in sortedKeys:
						parent, _, thisKey = key.rpartition("::")
						ident = _getIdentifier(key)
						f.write("\t\t\t\t\t\t['" + ident + "', ")
						if parent:
							f.write("'" + _getIdentifier(parent) + "', ")
						else:
							f.write("'<{}_root>',".format(threadScriptId))
						f.write(str(report[key][0]))
						f.write(", ")
						f.write(str(report[key][0]))
						f.write("],\n")

						exclusiveIdent = _getIdentifier(key + "::<inside " +thisKey + ">")
						f.write("\t\t\t\t\t\t['" + exclusiveIdent + "', ")
						f.write("'" + ident + "', ")
						f.write(str(max(report[key][1], 0.0000000001)))
						f.write(", ")
						f.write(str(max(report[key][1], 0.0000000001)))
						f.write("],\n")

					f.write(_blocks[1].format(threadScriptId, threadId))

					itemfmt = "[ \"{}\", {}, {}, {}, {}, {}, {}, {}, {}, {},\n"
					printed = set()
					first = True
					for key in sortedKeys:
						reportEntry = report[key]
						reportIncMean = reportEntry[Position.Inclusive] / reportEntry[Position.Count]
						reportExcMean = reportEntry[Position.Exclusive] / reportEntry[Position.Count]

						if key in printed:
							continue
						if key.find("::") != -1:
							continue
						if not first:
							f.write("\t\t\t\t\t],\n")
						f.write("\t\t\t\t\t")
						f.write(
							itemfmt.format(
								key,
								reportEntry[Position.Inclusive],
								reportEntry[Position.Exclusive],
								reportEntry[Position.Count],
								reportEntry[Position.MaxInc],
								reportEntry[Position.MinInc],
								reportIncMean,
								reportEntry[Position.MaxExc],
								reportEntry[Position.MinExc],
								reportExcMean,
							)
						)

						SharedLocals.totalExc += reportEntry[Position.Exclusive]
						SharedLocals.totalCount += reportEntry[Position.Count]
						SharedLocals.maxExcMean = max(SharedLocals.maxExcMean, reportExcMean)
						SharedLocals.maxIncMean = max(SharedLocals.maxIncMean, reportIncMean)
						SharedLocals.maxExcMax = max(SharedLocals.maxExcMax, reportEntry[Position.MaxExc])
						SharedLocals.maxIncMax = max(SharedLocals.maxIncMax, reportEntry[Position.MaxInc])
						SharedLocals.maxExcMin = max(SharedLocals.maxExcMin, reportEntry[Position.MinExc])
						SharedLocals.maxIncMin = max(SharedLocals.maxIncMin, reportEntry[Position.MinInc])
						f.write("\t\t\t\t\t\t[")

						_recurseHtml(report, sortedKeys, key + "::", printed, itemfmt, 6)
						first = False

					f.write(
						"\t\t\t\t\t]"
						"\n\t\t\t\t]"
					)
					f.write("\n\t\t\t\tvar totals_{} = [{}, {}, {}, {}, {}, {}, {}, {}]\n".format(
						threadScriptId, SharedLocals.totalExc, SharedLocals.totalCount,
						SharedLocals.maxIncMax, SharedLocals.maxIncMin, SharedLocals.maxIncMean,
						SharedLocals.maxExcMax, SharedLocals.maxExcMin, SharedLocals.maxExcMean,
					))
					annotationData = ''
					for annotation in annotations:
						txt, annotationThreadId, _, relativeTime = annotation
						if annotationThreadId == numericThreadId:
							if annotationData == '':
								annotationData = '<div style="border:1px solid black; background-color:#ccf; width:100%;padding:10px;"><h3>Notes</h3><ul>'
							annotationData += '<li>At <strong>' + _formatTime(relativeTime) + ':</strong> ' + txt + '</li>'
					
					if annotationData != '':
						annotationData += '</ul></div>'
							
					f.write(_blocks[2].format(threadScriptId, threadId, annotationData))

				f.write(_htmlHeader.format(name, " (Frame #{})".format(frameId) if frameId is not None else ""))

				for threadId, report in threadreports.items():
					if threadId == threading.current_thread().ident and __name__ != "__main__":
						continue
					else:
						_printReportHtml(report, "Worker Thread {}".format(threadId), threadId)

				if threading.current_thread().ident in threadreports and __name__ != "__main__":
					_printReportHtml(threadreports[threading.current_thread().ident], "Main Thread", threading.current_thread().ident)

				if len(threadreports) != 1:
					_printReportHtml(fullreport, "CUMULATIVE", 0)

				f.write(_htmlFooter)

		else:
			output("Perf reports:")

			def _recurse(report, sortedKeys, prefix, replacementText, printed, itemfmt):
				prev = (None, None)

				for key in sortedKeys:
					if key in printed:
						continue

					if key.startswith(prefix):
						printkey = key.replace(prefix, replacementText, 1)
						if printkey.find("::") != -1:
							continue
						if prev != (None, None):
							reportEntry = report[prev[1]]
							reportIncMean = reportEntry[Position.Inclusive] / reportEntry[Position.Count]
							reportExcMean = reportEntry[Position.Exclusive] / reportEntry[Position.Count]
							output(
								itemfmt.format(
									prev[0],
									_formatTime(reportEntry[Position.Inclusive]),
									_formatTime(reportEntry[Position.Exclusive]),
									reportEntry[Position.Count],
									_formatTime(reportEntry[Position.MinInc]),
									_formatTime(reportEntry[Position.MaxInc]),
									_formatTime(reportIncMean),
									_formatTime(reportEntry[Position.MinExc]),
									_formatTime(reportEntry[Position.MaxExc]),
									_formatTime(reportExcMean),
								)
							)
							printed.add(prev[1])
							_recurse(report, sortedKeys, prev[1] + "::", replacementText[:-4] + " \u2502  " + " \u251c\u2500 ", printed, itemfmt)
						prev = (printkey, key)

				if prev != (None, None):
					printkey = prev[0].replace("\u251c", "\u2514")
					reportEntry = report[prev[1]]
					reportIncMean = reportEntry[Position.Inclusive] / reportEntry[Position.Count]
					reportExcMean = reportEntry[Position.Exclusive] / reportEntry[Position.Count]
					output(
						itemfmt.format(
							printkey,
							_formatTime(reportEntry[Position.Inclusive]),
							_formatTime(reportEntry[Position.Exclusive]),
							reportEntry[Position.Count],
							_formatTime(reportEntry[Position.MinInc]),
							_formatTime(reportEntry[Position.MaxInc]),
							_formatTime(reportIncMean),
							_formatTime(reportEntry[Position.MinExc]),
							_formatTime(reportEntry[Position.MaxExc]),
							_formatTime(reportExcMean),
						)
					)
					printed.add(prev[1])
					_recurse(report, sortedKeys, prev[1] + "::", replacementText[:-4] + "    " + " \u251c\u2500 ", printed, itemfmt)

			def _alteredKey(key):
				return re.sub("([^:]*::)", "    ", key)

			def _printReport(report, threadId):
				if not report:
					return

				maxlen = len(str(threadId))
				totalcount = 0
				for key in report:
					maxlen = max(len(_alteredKey(key)), maxlen)
					totalcount += report[key][2]

				output("")
				linefmt = "+={{:=<{}}}=+============+============+===========+============+============+============+============+============+============+".format(maxlen)
				line = linefmt.format('')
				output(line)
				headerfmt = "| {{:<{}}} | INCLUSIVE  | EXCLUSIVE  |   CALLS   |  INC_MIN   |  INC_MAX   |  INC_MEAN  |  EXC_MIN   |  EXC_MAX   |  EXC_MEAN  |".format(maxlen)
				output(headerfmt.format(threadId))
				output(line)
				itemfmt = "| {{:{}}} | {{:>10}} | {{:>10}} | {{:>9}} | {{:>10}} | {{:>10}} | {{:>10}} | {{:>10}} | {{:>10}} | {{:>10}} |".format(maxlen)
				printed = set()
				sortedKeys = sorted(report, reverse=True, key=lambda x: report[x][0] if reportMode == ReportMode.TREE else report[x][1])
				total = 0
				for key in sortedKeys:
					if key in printed:
						continue
					if key.find("::") != -1:
						continue
					reportEntry = report[key]
					output(
						itemfmt.format(
							key,
							_formatTime(reportEntry[Position.Inclusive]),
							_formatTime(reportEntry[Position.Exclusive]),
							reportEntry[Position.Count],
							_formatTime(reportEntry[Position.MinInc]),
							_formatTime(reportEntry[Position.MaxInc]),
							_formatTime(reportEntry[Position.Inclusive] / report[key][Position.Count]),
							_formatTime(reportEntry[Position.MinExc]),
							_formatTime(reportEntry[Position.MaxExc]),
							_formatTime(reportEntry[Position.Exclusive] / report[key][Position.Count]),
						)
					)
					if reportMode == ReportMode.FLAT:
						total += reportEntry[Position.Exclusive]
					else:
						total += reportEntry[Position.Inclusive]
					_recurse(report, sortedKeys, key + "::", " \u251c\u2500 ", printed, itemfmt)

				output(line)

			for threadId, report in threadreports.items():
				if threadId == threading.current_thread().ident:
					continue
				else:
					_printReport(report, "Worker Thread {}".format(threadId))

			_printReport(threadreports[threading.current_thread().ident], "Main Thread")
			if len(threadreports) != 1:
				_printReport(fullreport, "CUMULATIVE")

if __name__ == "__main__":
	class Operation:
		Enter = 0
		Exit = 1
		Note = 2
	if len(sys.argv) < 2:
		print("Syntax: perf_timer.py <metricsFilename> <outputHtmlFilename> <applicationName> [minFrameTime (ms)]")
		sys.exit(1)
	if sys.argv[1] == "test":
		if len(sys.argv) != 4 and len(sys.argv) != 5:
			print("Syntax: perf_timer.py test <outputHtmlFilename> <applicationName> [threaded]")
			sys.exit(1)
		threads = 1
		if len(sys.argv) == 5 and sys.argv[4] == "threaded":
			threads = 3
		class Shared:
			now = 0
		def test(recursion, name, iter, frame, thread):
			import random
			with PerfTimer(name, frame) as pt:
				pt.threadId = thread
				Shared.now += random.randint(10000, 20000)
				if recursion < 3:
					for i in range(random.randint(0, 3)):
						test(recursion + 1, "DemoFunc_{}_{}_{}".format(iter, recursion, i), frame, thread)
				Shared.now += random.randint(10000, 20000)
		for i in range(100):
			for t in range(threads):
				print(i)
				for j in range(3):
					test(0, "DemoFunc_0_{}".format(j), j, i, t)
	elif sys.argv[1] == "test_write_json" or sys.argv[1] == "test_write_binary":
		if len(sys.argv) != 2 and len(sys.argv) != 3:
			print("Syntax: perf_timer.py " + sys.argv[1] + " [threaded]")
			sys.exit(1)
		threads = 1
		if len(sys.argv) == 3 and sys.argv[2] == "threaded":
			threads = 3
		datas = []
		class Shared:
			now = 0
		def test(recursion, name, iter, frame, thread):
			import random
			import time
			import math
			datas.append([Operation.Enter, thread, frame, Shared.now, name])
			Shared.now += random.randint(10000, 20000)
			if recursion < 3:
				for i in range(random.randint(0, 3)):
					test(recursion + 1, "DemoFunc_{}_{}_{}".format(iter, recursion, i), iter, frame, thread)
			Shared.now += random.randint(10000, 20000)
			datas.append([Operation.Exit, thread, frame, Shared.now, name])
		for i in range(100):
			for t in range(threads):
				print(i)
				for j in range(3):
					test(0, "DemoFunc_0_{}".format(j), j, i, t)
		import json
		if sys.argv[1] == "test_write_json":
			with open("test_json_data.json", "w") as f:
				json.dump(datas, f)
		else:
			import struct
			with open("test_binary_data.bin", "wb") as f:
				f.write(struct.pack("<L", 0xFA57))
				f.write(struct.pack("<L", len(datas)))
				for data in datas:
					f.write(struct.pack("<bQiQH", data[0], data[1], data[2], int(data[3]), len(data[4])))
					if sys.version_info[0] >= 3:
						f.write(data[4].encode("ascii"))
					else:
						f.write(data[4])
		sys.exit(0)
	else:
		if len(sys.argv) != 4 and len(sys.argv) != 5:
			print("Syntax: perf_timer.py metricsFilename outputHtmlFilename applicationName [minFrameTime (ms)]")
			sys.exit(1)
		if len(sys.argv) == 5:
			PerfTimer.setMinFrameTime(float(sys.argv[4]))
		with open(sys.argv[1], "rb") as f:
			import struct

			print("Processing file")
			if struct.unpack("<L", f.read(4))[0] == 0xFA57:
				print("Found FA57 header. Processing as binary...")
				recordings = []
				count = struct.unpack("<L", f.read(4))[0]
				print("File provides {} events. Loading data...".format(count))
				i = 0
				for _ in range(count):
					i += 1
					if i % 10000 == 0:
						sys.stdout.write("\r... {} ({:.1f}%)".format(i, i/count*100))
					line = list(struct.unpack("<bQiQH", f.read(1+8+4+8+2)))
					name = b""
					name = f.read(line[4])
					line[4] = name.replace(b"::", b".")
					recordings.append(line)
				print("\rData loaded, processing...")

			else:
				f.seek(0, os.SEEK_SET)
				import json
				print("File is not binary. Processing as JSON...")
				recordings = json.load(f)
				print("File provides {} events, processing...".format(len(recordings)))

		stacks = {}
		lastEnd = {}
		i = 0
		for recording in recordings:
			i += 1
			if i % 10000 == 0:
				sys.stdout.write("\r... {} ({:.1f}%)".format(i, i/len(recordings)*100))
			operation, threadId, frameId, timestamp, name = recording
			timestamp /= 1000 * 1000 * 1000
			if sys.version_info[0] >= 3 and isinstance(name, bytes):
				name = name.decode("ascii")

			if operation == Operation.Enter:
				timer = PerfTimer(name, frameId if frameId >= 0 else None)
				timer.threadId = threadId
				try:
					prev = stacks[threadId][-1]
					prev.exclusive += timestamp - prev.excstart
					timer.scopeName = prev.scopeName + "::" + timer.blockName

					stacks[threadId].append(timer)
				except:
					lastEndThisFrameAndThread = lastEnd.get(threadId, {}).get(frameId, None)
					if lastEndThisFrameAndThread is not None:
						lastEnd.setdefault(threadId, {})[frameId] = None
						duration = timestamp - lastEndThisFrameAndThread
						PerfTimer.perfQueue.append(
							("<unknown>", duration, duration, threadId, frameId, lastEndThisFrameAndThread, timestamp))
						
					stacks[threadId] = [timer]

				timer.incstart = timestamp
				timer.excstart = timestamp

			elif operation == Operation.Exit:
				timer = stacks[threadId][-1]
				try:
					prev = stacks[threadId][-2]
					prev.excstart = timestamp
				except:
					lastEnd.setdefault(threadId, {})[frameId] = timestamp
					pass

				timer.exclusive += timestamp - timer.excstart
				timer.inclusive = timestamp - timer.incstart

				PerfTimer.perfQueue.append(
					(timer.scopeName, timer.inclusive, timer.exclusive, timer.threadId, timer.frame, timer.incstart, timestamp))
				stacks[threadId].pop()
			elif operation == Operation.Note:
				PerfTimer.annotations.append((name, threadId, frameId, timestamp))
			else:
				print("\rInvalid operation: {}".format(operation))
				exit(1)
				
		print("\rFinished processing {} events. Generating output...".format(len(recordings)))

	PerfTimer.PrintPerfReport(ReportMode.HTML, sys.argv[2], sys.argv[3])

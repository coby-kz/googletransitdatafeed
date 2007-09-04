#!/usr/bin/python2.4

# Copyright (C) 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Validates a Google Transit Feed Specification feed.
#
#
# usage: feedvalidator.py [options] feed_filename
#
# options:
#   --version             show program's version number and exit
#   -h, --help            show this help message and exit
#   -n, --noprompt        do not prompt for feed location or load output in
#                         browser
#   -o FILE, --output=FILE
#                         write html output to FILE

import codecs
import optparse
import os.path
import time
import transitfeed
import sys
import webbrowser

DEFAULT_UNUSED_LIMIT = 5  # number of unused stops to print

def ProblemCountText(problem_count):
  if (problem_count == 1):
    return 'one issue'
  else:
    return '%d issues' % problem_count

class HTMLCountingProblemReporter(transitfeed.ProblemReporter):
  def __init__(self):
    transitfeed.ProblemReporter.__init__(self)
    self._output = []
    self.count = 0
    self.unused_stops = []  # [(stop_id, stop_name)...]

  def UnusedStop(self, stop_id, stop_name):
    self.count += 1
    self.unused_stops.append((stop_id, stop_name))

  def _Report(self, e):
    self.count += 1
    d = e.GetDict()
    for k in ('file_name', 'feedname', 'column_name'):
      if k in d.keys():
        d[k] = '<code>%s</code>' % d[k]
    problem_text = e.FormatProblem(d).replace('\n', '<br>')
    self._output.append('<li>')
    self._output.append('<div class="problem">%s</div>' %
                        transitfeed.EncodeUnicode(problem_text))
    try:
      self._output.append('in line %d of <code>%s</code><br>\n' %
                           (e.row_num, e.file_name))
      row = e.row
      headers = e.headers
      column_name = e.column_name
      table_header = ''  # HTML
      table_data = ''  # HTML
      for header, value in zip(headers, row):
        attributes = ''
        if header == column_name:
          attributes = ' class="problem"'
        table_header += '<th%s>%s</th>' % (attributes, header)
        table_data += '<td%s>%s</td>' % (attributes, value)
      self._output.append('<table><tr>%s</tr>\n' % table_header)
      # Make sure self._output contains strings with UTF-8 or binary data, not
      # unicode
      self._output.append('<tr>%s</tr><table>\n' %
                          transitfeed.EncodeUnicode(table_data))
    except AttributeError, e:
      pass  # Hope this was getting an attribute from e ;-)
    self._output.append('</li><br>\n')

  def _UnusedStopSection(self):
    unused = []
    unused_count = len(self.unused_stops)
    if unused_count:
      if unused_count == 1:
        unused.append('%d.<br>' % self.count)
        unused.append('<div class="unused">')
        unused.append('one stop was found that wasn\'t')
      else:
        unused.append('%d&ndash;%d.<br>' %
                      (self.count - unused_count + 1, self.count))
        unused.append('<div class="unused">')
        unused.append('%d stops were found that weren\'t' % unused_count)
      unused.append(' used in any trips')
      if unused_count > DEFAULT_UNUSED_LIMIT:
        self.unused_stops = self.unused_stops[:DEFAULT_UNUSED_LIMIT]
        unused.append(' (the first %d are shown below)' %
                      len(self.unused_stops))
      unused.append(':<br>')
      unused.append('<table><tr><th>stop_name</th><th>stop_id</th></tr>')
      for stop_id, stop_name in self.unused_stops:
        unused.append('<tr><td>%s</td><td>%s</td></tr>' % (stop_name, stop_id))
      unused.append('</table><br>')
      unused.append('</div>')
    return ''.join(unused)

  def GetOutput(self, feed_location):
    if problems.count:
      summary = ('<span class="fail">%s found</span>' %
                 ProblemCountText(problems.count))
    else:
      summary = '<span class="pass">feed validated successfully</span>'

    basename = os.path.basename(feed_location)
    feed_path = (feed_location[:feed_location.rfind(basename)], basename)

    output_contents = """
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/> 
<title>FeedValidator: %s</title>
<style>
body {font-family: Georgia, serif}
.path {color: gray}
div.problem {max-width: 500px}
td,th {background-color: khaki; padding: 2px; font-family:monospace}
td.problem,th.problem {background-color: dc143c; color: white; padding: 2px; font-family:monospace}
table {border-spacing: 5px 0px; margin-top: 3px}
span.pass {background-color: lightgreen}
span.fail {background-color: yellow}
.pass, .fail {font-size: 16pt; padding: 3px}
ol,.unused {padding-left: 40pt}
.footer {font-size: 10pt}
</style>
</head>
<body>
Validation results for feed:<br>
<code><span class="path">%s</span><b>%s</b></code><br><br>
%s
<ol>%s</ol>
%s
<div class="footer">
Generated by <a href="http://code.google.com/p/googletransitdatafeed/wiki/FeedValidator">
FeedValidator</a> version %s on %s.
</div>
</body>
</html>""" % (feed_path[1], feed_path[0], feed_path[1],
              summary, ''.join(self._output),
              self._UnusedStopSection(),
              transitfeed.__version__, time.asctime())
    return output_contents

if __name__ == '__main__':
  parser = optparse.OptionParser(usage='usage: %prog [options] feed_filename',
                                 version='%prog '+transitfeed.__version__)
  parser.add_option('-n', '--noprompt', action='store_false',
                    dest='manual_entry',
                    help='do not prompt for feed location or load output in browser')
  parser.add_option('-o', '--output', dest='output', metavar='FILE',
                    help='write html output to FILE')
  parser.set_defaults(manual_entry=True, output='validation-results.html')
  (options, args) = parser.parse_args()
  manual_entry = options.manual_entry
  if not len(args) == 1:
    if manual_entry:
      feed = raw_input('Enter Feed Location: ')
    else:
      print >>sys.stderr, parser.format_help()
      print >>sys.stderr, '\n\nYou must provide the path of a single feed\n\n'
      sys.exit(2)
  else:
    feed = args[0]

  feed = feed.strip('"')
  print 'validating %s' % feed
  problems = HTMLCountingProblemReporter()
  loader = transitfeed.Loader(feed, problems=problems, extra_validation=True)
  loader.Load()

  exit_code = 0
  if problems.count:
    print 'ERROR: %s found' % ProblemCountText(problems.count)
    exit_code = 1
  else:
    print 'feed validated successfully'

  output_filename = options.output
  output_file = open(output_filename, 'w')
  output_file.write(problems.GetOutput(os.path.abspath(feed)))
  output_file.close()
  if manual_entry:
    webbrowser.open('file://%s' % os.path.abspath(output_filename))

  sys.exit(exit_code)

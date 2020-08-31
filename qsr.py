#!/usr/bin/env python3
#coding:utf-8
"""Simple HTTP Server With Upload.
This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.
see: https://gist.github.com/UniIsland/3346170
"""
import sys, os, socket
from socketserver import ThreadingMixIn
from http.server import SimpleHTTPRequestHandler, HTTPServer
import posixpath
import http.server
import urllib.request, urllib.parse, urllib.error
import html
import shutil
import mimetypes
import re
from io import BytesIO
import getopt
import webbrowser
HOST = socket.gethostname()
ALIAS=""
LOG_FILE_ABS_PATH=""
LOG_MESSAGE=True
CSS="""
<script type="text/javascript">
function altRows(id){
    if(document.getElementsByTagName){
        var table = document.getElementById(id);
        var rows = table.getElementsByTagName("tr");
        for(i = 0; i < rows.length; i++){
            if(i % 2 == 0){
                rows[i].className = "evenrowcolor";
            }else{
                rows[i].className = "oddrowcolor";
            }
        }
    }
}
window.onload=function(){
    altRows('alternatecolor');
}
</script>
<style type="text/css">
table.altrowstable {
    font-family: monospace,PF_Ubuntu,Consolas,Monaco,Ubuntu Mono,UbuntuMono,Microsoft YaHei,PingFangSC-Medium;
    font-size:14px;
    color:#333333;
    border-width: 1px;
    border-color: #a9c6c9;
    border-collapse: collapse;
}
table.altrowstable th {
    border-width: 1px;
    padding: 8px;
    border-style: solid;
    border-color: #a9c6c9;
}
table.altrowstable td {
    border-width: 1px;
    padding: 8px;
    border-style: solid;
    border-color: #a9c6c9;
}
.oddrowcolor{
    background-color:#d4e3e5;
}
.evenrowcolor{
    background-color:#c3dde0;
}
<!--
a:link { text-decoration: none;color: black}
a:active { text-decoration:blink}
a:hover { text-decoration:underline;color: red}
a:visited { text-decoration: none;color: black}
-－>
</style>
"""
PREVIEW_HTML="""
<html>
<head>
     <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
     <meta http-equiv="Pragma" content="no-cache" />
     <title>{filepath:}</title>
</head>
<script language="JavaScript">
     onload = function()
     {{
          document.nameOfIFrame.document.body.style.fontFamily = "PF_Ubuntu,Consolas,Monaco,Ubuntu Mono,UbuntuMono,Microsoft YaHei,PingFangSC-Medium";
     }}
</script>
     <frameset >
         <frame name="refcode" marginwidth=80% src="{filepath:}">
     </frameset>
</html>
"""
def log(*args):
    if LOG_FILE_ABS_PATH=="":
        pass
    else:
        with open(LOG_FILE_ABS_PATH,"a") as file:
            logstring=" ".join(args)
            file.write(logstring+"\n")
class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Simple HTTP request handler with GET/HEAD/POST commands.
    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method. And can reveive file uploaded
    by client.
    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.
    """
    def log_message(self, format, *args):
        if LOG_MESSAGE:
            super().log_message(format,*args)

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.close()
    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()
    def do_POST(self):
        """Serve a POST request."""
        r, info,logmsg = self.deal_post_data()
        if r:
            log(info, "Client IP:", self.client_address[0],"")
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<head>\n<meta content=\"text/html; charset=UTF-8\" http-equiv=\"Content-Type\">\n".encode())
        f.write("""<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0,minimum-scale=1.0,user-scalable=0" />""".encode())
        f.write(b"\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<div align=\"center\"><h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Upload Success</strong><br>")
        else:
            f.write(b"<strong>Upload Fail</strong><br>")
        f.write(info.encode())
        f.write(("<br><br><br><a href=\"%s\" > <font color=\"green\">Click here to go back!!!</font></a>" % self.headers['referer']).encode())
        f.write(b"</a>.</small></div></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def deal_post_data(self):
        content_type = self.headers['content-type']
        if not content_type:
            return (False, "Content-Type header doesn't contain boundary","Content-Type header doesn't contain boundary")
        boundary = content_type.split("=")[1].encode()
        remainbytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remainbytes -= len(line)
        if not boundary in line:
            return (False, "Content NOT begin with boundary","Content NOT begin with boundary")
        line = self.rfile.readline()
        remainbytes -= len(line)
        fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode())
        if len(fn)==0:
            return (False, "Can't find out file name...","Fail to find name.")
        if not fn[0]:
            return (False, "File name is null.", "File name is null.")

        path = self.translate_path(self.path)
        fn = os.path.join(path, fn[0])
        relative_file_path=fn.replace("\\","/").replace(os.getcwd().replace("\\","/").rstrip("/"),"",1)
        line = self.rfile.readline()
        remainbytes -= len(line)
        line = self.rfile.readline()
        remainbytes -= len(line)
        try:
            out = open(fn, 'wb')
        except IOError:
            return (False, "Can't create file to write, do you have permission to write?","No permission: {}".format(fn))
        preline = self.rfile.readline()
        remainbytes -= len(preline)
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            if boundary in line:
                preline = preline[0:-1]
                if preline.endswith(b'\r'):
                    preline = preline[0:-1]
                out.write(preline)
                out.close()
                return (True, "File '{}' upload success!".format(relative_file_path),"Success: {}".format(fn))
            else:
                out.write(preline)
                preline = line
        return (False, "Unexpect Ends of data.","Unexpect Ends of data.")
    def send_head(self):
        """Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        path = self.translate_path(self.path)
        arg =urllib.parse.unquote(urllib.parse.urlparse(self.path)[4])
        request_url =urllib.parse.unquote(urllib.parse.urlparse(self.path)[2])
        dummyfolder=os.path.split(request_url)[0]
        is_preview=False
        file_name=""
        if os.path.split(request_url)[-1]=='preview.html':
            is_preview=True
            file_name=arg
            path = os.getcwd()+dummyfolder + "/" + file_name
        path.replace("\\","/")
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path,arg)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        if is_preview and ctype=='text/plain':
            self.send_response(200)
            self.send_header("Content-type", 'text/html')
            fs = os.fstat(f.fileno())
            self.send_header('charset', "utf-8")
            fstream=BytesIO()
            dic={"filepath": file_name}
            fstream.write(PREVIEW_HTML.format(**dic).encode())
            self.send_header("Content-Length", str(fstream.tell()))
            fstream.seek(0)
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return fstream
        else:
            self.send_response(200)
            self.send_header("Content-type", ctype)
            fs = os.fstat(f.fileno())
            self.send_header("ContentType", "text/html")
            self.send_header('charset', "utf-8")
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
    def list_directory(self, path,arg=""):
        """Helper to produce a directory listing (absent index.html).
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """
        try:
            folders = [i.replace("\\",'/') for i in os.listdir(path.replace("\\",'/')) if os.path.isdir(path.rstrip("/")+"/"+i)]
            files=[i.replace("\\",'/') for i in os.listdir(path.replace("\\",'/')) if os.path.isfile(path.rstrip("/")+"/"+i)]
            folders=sorted(folders,key=lambda x:x.lower())
            files=sorted(files,key=lambda  x:x.lower())
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        folder_and_files=folders+files
        f = BytesIO()
        displaypath = html.escape(urllib.parse.unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<head>\n<meta content=\"text/html; charset=UTF-8\" http-equiv=\"Content-Type\">\n".encode())
        f.write(("<html>\n<title>{}:{}</title>\n".format(ALIAS,displaypath)).encode())
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">'.encode())
        f.write("<html>\n<head>\n<meta content=\"text/html; charset=UTF-8\" http-equiv=\"Content-Type\">"
                "<meta http-equiv=\"Pragma\" content=\"no-cache\" />\n".encode())
        f.write("""<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0,minimum-scale=1.0,user-scalable=0" />""".encode())
        f.write(CSS.encode())
        f.write(("<title>%s</title>\n</head>\n" % displaypath).encode())
        f.write(("""
                    <body>\n<h2 align=\"center\"> <font color=\"blue\"  face='Ubuntu,sans-serif'>{}</font>
                    <br><code ><font color=\"red\" face='monospace'>{}</font></code>
                    </h2>\n""".format(ALIAS, displaypath)).encode())
        f.write(b"<div align=\"center\"><form align=\"center\" ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<input name=\"file\" type=\"file\"/>")
        f.write(b"<input type=\"submit\" value=\"Upload\"/></form></div>\n")
        f.write(b"\n<table align=\"center\" class=\"altrowstable\" id=\"alternatecolor\">\n")
        for name in folder_and_files:
            fullname = os.path.join(path.replace("\\",'/'), name.replace("\\",'/'))
            displayname = linkname = name.replace("\\",'/')
            link_url='preview.html'+'?'+(linkname)
            # Append / for dirctories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
                link_url=linkname
            else:
                if self.guess_type(linkname)!='text/plain':
                    link_url = linkname

            download_area=   "{}".format(
                                        "" if os.path.isdir(fullname)
                                            else
                                                """<a href=\"{}\" download="" >{}</a>""".format("./"+name, "DownLoad"))
            f.write("<tr>".encode())
            f.write(('<td width=500  word-break=break-all word-wrap=break-word ><a href="%s">%s</a></td>'
                    % (link_url, html.escape(displayname))).encode('utf-8'))
            f.write("""<td width="80">{}</td>\n""".format(download_area).encode())
            f.write("</tr>".encode())
        f.write(b"</table>\n\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("contentType", "text/html")
        self.send_header('charset',"utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f
    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.
        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)
        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split('/')
        words = [_f for _f in words if _f]
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path
    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.
        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).
        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.
        """
        try:
            shutil.copyfileobj(source, outputfile)
        except ConnectionResetError:
            pass

    def guess_type(self, path):
        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init() # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream', # Default
        })
    txt_file_extensions=['cpp','c','h','hpp',
                         'java','py','cfg','ini','txt','frag','vert','elf','xml','md','qpa',
                         'php','asp','cs','bat','sh','csv','reg','y','log',
                         'desktop'
                         ]
    for i in txt_file_extensions:
        extensions_map["."+i.lower().lstrip(".")]='text/plain'


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass
helpMsg=\
"""qsr.py tips:
    qsr.py is only for python3.
    You'd better use Chrome or Firefox. QQbrowser has some bugs.
    usage example: python3 qsr --dir yourdir --port portnumber --logfile mylog.txt --alias SiteName
    [--dir]:     yourdir shall not contain the qsr.py to avoid overwrite. It is the root dir of the website.
    [--port]:    port is default set to 80(windows)/8080(linux). If you choose 80 on linux, you must run as sudo.
    [--logfile]: log feature is turned off by default.
    [--alias]:  you can config your web site name via alias. By default, is your username.
    [--quiet]:  This will not open your browser and disable the log in the terminal.
    """
def parseArgs(args):
    opts,values=getopt.getopt(args,'-d:-p:-l:-a:-h:q',['help',"dir=",'port=','help','logfile=','alias=',"quiet"])
    configs={}
    for key,value in opts:
        if key in ('-h','--help'):
            print(helpMsg)
            sys.exit(0)
        if key in ('-d','--dir'):
            configs['dir']=value
        if key in ('-p','--port'):
            configs["port"]=value
        if key in ('-l','--logfile'):
            configs['logfile']=value
        if key in ('-a','--alias'):
            configs['alias']=value
        if key in ("-q","--quiet"):
            configs['quiet']=True
    return configs
if __name__ == '__main__':
    qsr_dir=os.path.dirname(__file__).replace('\\','/').rstrip('/')
    port=80
    dir=""
    configs={}
    if sys.argv.__len__()>1:
        configs=parseArgs(sys.argv[1:])
    dir=configs.get('dir','!qsr_website_root')
    if os.path.isdir(dir):
        pass
    else:
        if  not os.path.exists(dir):
            os.mkdir(dir)
            print("Create {} for you as the website root folder".format(dir))
        else:
            print("Please specify a subfolder as website root folder using -a")
            exit(1)
    os.chdir(dir)
    dir=os.getcwd().replace("\\",'/').rstrip('/')
    if dir==qsr_dir or dir in qsr_dir:
        print("Please give a valid dir as your websit root.\nYou had better use a subfolder under '{}'".format(qsr_dir))
    else:
        port=int(configs.get('port',80 if os.path.exists("c:\\windows") else 8080))
        logfileName=configs.get('logfile',"")
        if logfileName=="":
            pass
        else:
            LOG_FILE_ABS_PATH="{}{}{}".format(qsr_dir.replace("/",os.path.sep),os.path.sep,logfileName)
            print("Log file is:\n    {}".format(LOG_FILE_ABS_PATH))
        ALIAS=configs.get('alias',HOST)
    server=None
    server = ThreadingSimpleServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    if server:
        if not configs.get("quiet",False):
            webbrowser.open("http://127.0.0.1:{:d}".format(port))
        else:
            LOG_MESSAGE=False
        print("Http server is runing on:\n    {}\nWorking Folder:\n    {}\nPort:\n    {}".format(HOST,dir.replace("/",os.path.sep),port))
        try:
            while 1:
                sys.stdout.flush()
                server.handle_request()
        except KeyboardInterrupt:
            print("\nShutting down server per users request.")
    else:
        print("Fail to lunch the server")
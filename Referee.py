#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import time,sys,traceback,math,numpy
LOGLEVEL={0:"DEBUG",1:"INFO",2:"WARN",3:"ERR",4:"FATAL"}
LOGFILE=sys.argv[0].split(".")
LOGFILE[-1]="log"
LOGFILE=".".join(LOGFILE)
def log(msg,l=1,end="\n",logfile=None,fileonly=False):
    st=traceback.extract_stack()[-2]
    lstr=LOGLEVEL[l]
    now_str="%s %03d"%(time.strftime("%y/%m/%d %H:%M:%S",time.localtime()),math.modf(time.time())[0]*1000)
    if l<3:
        tempstr="%s [%s,%s:%d] %s%s"%(now_str,lstr,st.name,st.lineno,str(msg),end)
    else:
        tempstr="%s [%s,%s:%d] %s:\n%s%s"%(now_str,lstr,st.name,st.lineno,str(msg),traceback.format_exc(limit=5),end)
    if not fileonly:
        print(tempstr,end="")
    if l>=1 or fileonly:
        if logfile==None:
            logfile=LOGFILE
        with open(logfile,"a") as f:
            f.write(tempstr)

from http.server import BaseHTTPRequestHandler
try:
    from http.server import ThreadingHTTPServer
    HTTPServerClass=ThreadingHTTPServer
except ImportError:
    from http.server import HTTPServer
    HTTPServerClass=HTTPServer
    log("import ThreadingHTTPServer failed, use HTTPServer instead")

class MyTimeoutException(Exception):
    pass

class MyHTTPServer(HTTPServerClass):
    def serve_forever(self):
        log("server is on %s"%(self.socket.getsockname(),))
        log("server context stats is %s"%(self.socket.context.cert_store_stats(),))
        log("server hostname is %s"%(self.socket.server_hostname,))
        HTTPServerClass.serve_forever(self)

    def _handle_request_noblock(self):
        try:
            request,client_address=self.get_request()
        except OSError as e:
            signal.alarm(0)
            #log("OSError: %s"%(e),l=2)
            return 1
        except MyTimeoutException:
            #log("normal timeout")
            return 2
        except:
            signal.alarm(0)
            log("uncaught exception",l=3)
            return 3

        if self.verify_request(request, client_address):
            try:
                self.process_request(request, client_address)
            except:
                self.handle_error(request, client_address)
                self.shutdown_request(request)
        else:
            self.shutdown_request(request)
        return 0
    def get_request(self):
        def alarm_handle(signum,frame):
            raise MyTimeoutException("timeout!")
        #id=random.randint(0,65535)
        #log("%d: accepting new request"%(id))
        signal.signal(signal.SIGALRM,alarm_handle)
        signal.alarm(1)
        acc=self.socket.accept()
        signal.alarm(0)
        #log("%d: accpeted, cert: %s"%(id,acc[0].getpeercert()))
        return acc

class MyHTTPRequestHandler(BaseHTTPRequestHandler):    
    def log_message(self, format, *args):
        return

    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    def do_GET(self):
        log("%s from %s requesting %s"%(self.command,self.client_address,self.path))
        #self.headers contains many infos of client
        #self.path is the request path
        #self.rfile is the file to read from client
        #self.wfile is the file to write to response
        self._set_headers()
        reply_text="get!"
        reply_byte=reply_text.encode("utf8")
        self.wfile.write(reply_byte)
        return 0
        
    def do_POST(self):
        log("%s from %s requesting %s"%(self.command,self.client_address,self.path))
        content_length=int(self.headers.get('Content-Length',0))
        post_data=self.rfile.read(content_length)

        self._set_headers()
        reply_byte="got your post at %s"%(time.strftime("%y/%m/%d %H:%M:%S",time.localtime()),)
        reply_byte=reply_byte.encode("ascii")
        self.wfile.write(reply_byte)
        return 0

def run_server(port=67160):
    re_code=-1
    try:
        httpd=MyHTTPServer(('',port),MyHTTPRequestHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("KeyboardInterrupt")
        re_code=0
    except MyTimeoutException:
        log("normal timeout, but did not be catched",l=3)
        re_code=1
    except:
        log("server run error!",l=3)
        re_code=2
    finally:
        if "httpd" in locals().keys():
            httpd.server_close()
    log("quit run_server",l=2)
    return re_code

if __name__=="__main__":
    run_server()
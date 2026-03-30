#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
2018-06-25 shiming
"""

import os
import sys
import re
import json
import time
import subprocess
G_tw_token = ""
G_tw_account_id = ""
G_tw_account    = ""
G_tw_file_key   = ""
G_tw_http_ip    = ""
G_tw_init_data  = {}
G_bin_path      = os.path.dirname(os.path.dirname(__file__)).replace("\\", "/")
G_tw_proxy = {}
G_tw_api_key = ''


py_ver=str(sys.version_info[0])+"."+str(sys.version_info[1])
py_dict={"2.7":"py2lib", "3.7":"py3lib", "3.9":"py39lib", "3.10":"py310lib", "3.11":"py311lib", "3.12":"py312lib"}
if py_ver not in py_dict:
    raise Exception("Not support python version: ({}), only support ({})".format(py_ver, ', '.join(py_dict.keys())))
try:
    t_inside_path=os.path.dirname(__file__).replace("\\", "/")+"/"+py_dict[py_ver]
    t_inside_path in sys.path or sys.path.append(t_inside_path)
    import six
    import ctlib
    from websocket import create_connection
    import requests
    try:
        requests.packages.urllib3.disable_warnings()
    except:
        pass
except Exception as e:
    raise Exception("Import module(websocket, requests) fail. {}".format(e))

if six.PY2:
    from collections import Mapping
else:
    from collections.abc import Mapping


from twlib._con import _con
from twlib._con_local import _con_local
from twlib._client import _client
from twlib._module import _module
from twlib._module_e import _module_e
from twlib._lib import _lib
from twlib._dom import _dom
from twlib._compat import *

G_cgtw_session=requests.Session()
class tw:
    __version__="7.0"  #当前api版本
    global G_tw_token
    global G_tw_account_id
    global G_tw_account
    global G_tw_file_key
    global G_tw_http_ip	  #用于python上传下载, 格式: ip:port
    #global G_is_login	  #用于判断是否有登录
    global G_tw_init_data #初始化数据

    def __init__(self, http_ip='', account='', password='', **kwargs):
        u"""
         描述: 初始化, 备注:服务器IP,账号,密码都不填写的时候,会连接到客户端获取登陆信息
         调用: __init__(http_ip='', account='', password='')
              --> http_ip                   服务器IP, (str/unicode)
              --> account                   账号 (str/unicode)
              --> password                  密码 (str/unicode)
              --> proxy                     代理:如{"https_proxy": url},
                                                url="http://127.0.0.1:8080" 或者 "http://user:pass@127.0.0.1:8080" 或者 "socks5h://127.0.0.1:1080"用于http_ip为域名  或者 "socks5://127.0.0.1:1080"用于http_ip为ip                                    
         """           
        global G_tw_proxy
        global G_tw_totp_password
        global G_tw_api_key
        global G_tw_is_token_login
        t_proxy = kwargs.get("proxy", {})
        t_token = kwargs.get("token", "")
        if to_unicode(t_token).strip()!="":
            G_tw_is_token_login = True
        else:
            G_tw_is_token_login = False

        # 无效的代理参数
        if not isinstance(t_proxy, Mapping):
            proxy = {}
        G_tw_proxy = t_proxy
        G_tw_totp_password = kwargs.get("totp_password", '')
        G_tw_api_key = kwargs.get("api_key", "")
        tw.login._login(http_ip, account, password, t_token)
        
    def get_version(self): 
        u"""
         描述: 获取CGTeamwork软件的版本
         调用: get_version()   
         返回: 成功返回str
         """          
        return self.__version__

    #发送到web
    @staticmethod
    def send_web(controller, method, data_dict):
        u"""
         描述: post到后台
         调用: send_web(controller, method, data_dict)
               --> controller              控制器 (str/unicode)
               --> method                  方法 (str/unicode)
               --> data_dict               post的数据 (dict)
         返回: 按实际情况
         """          
        global G_tw_http_ip
        global G_tw_token
        global G_tw_is_token_login
        global G_tw_api_key
        if not isinstance(controller, basestring) or not isinstance(method, basestring) or not isinstance(data_dict, dict):
            raise Exception("send_web argv error ,there must be (str/unicode, str/unicode, dict)")

        try:
            if G_tw_is_token_login:
                data_dict["cgtw_api_key"] = G_tw_api_key
            
            res = _con.send(G_cgtw_session, G_tw_http_ip, G_tw_token, controller, method, data_dict)
        except  Exception as e:
            if repr(e).find("the token has expired")!=-1 or repr(e).find("please login")!=-1:
                global G_tw_init_data #初始化数据
                http_ip = G_tw_init_data["http_ip"]
                account = G_tw_init_data["account"]
                password = G_tw_init_data["password"]
                t_token = G_tw_init_data["token"]
                if to_unicode(http_ip).strip()!="" and to_unicode(account).strip()!="":
                    tw.login._login(http_ip, account, password, t_token)
                    res = _con.send(G_cgtw_session, G_tw_http_ip, G_tw_token, controller, method, data_dict)
                else:
                    raise Exception(e)

            else:
                raise Exception(e)
        return res
    
    @staticmethod
    def send_local_http(db, module, action, other_data_dict, type="send"):
        u"""
         描述: post到客户端的http server
         调用: send_local_http(db, module, action, other_data_dict, type="send")
               --> db                      数据库 (str/unicode)
               --> module                  模块 (str/unicode)
               --> action                  动作 (str/unicode)
               --> other_data_dict         post的数据 (dict)
               --> type                    类型 (str/unicode), send/get
               
         返回: 按实际情况
         """          
        if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(action, basestring) or \
           not isinstance(other_data_dict, dict) or not isinstance(type, basestring): #or type not in ['send','get']:
            raise Exception("send_local_http argv error ,there must be (str/unicode, str/unicode, str/unicode, dict, str/unicode)")
        
        return _con_local.send_http(module, db, action, other_data_dict, type)

    @staticmethod
    def send_local_socket(sign, method, data, type="get"):
        u"""
         描述: post到客户端的websocket server
         调用: send_local_socket(sign, method, data, type="get")
               --> sign                    标识 (str/unicode)
               --> method                  方法 (str/unicode)
               --> data                    post的数据 (dict)
               --> type                    类型 (str/unicode), send/get
         返回: 按实际情况
         """            
        if not isinstance(sign, basestring) or not isinstance(method, basestring) or not isinstance(data, dict) or not isinstance(type, basestring):
            raise Exception("send_local_socket argv error, there must be (str/unicode, str/unicode, dict, str/unicode)")
        return _con_local.send_socket(sign, method, data, type)

    class com:
        
        @staticmethod
        def get_os():
            u"""
            描述:获取操作系统(win/mac/linux)
            调用:get_os()
            """
            return _lib.get_os()
        
        @staticmethod
        def get_server_time():
            u"""
            描述: 获取CGTeamwork服务器的当前时间
            调用: get_server_time()   
            返回: 成功返回str, 2019-01-01 00:11:22
            """                 
            global G_tw_account_id	
            global G_tw_token
            if tw.login.is_login()==False:
                return ""
            return tw.send_web("com", "get_time", {})    
    
    class client:

        @staticmethod
        def get_argv_key(key):
            u"""
             描述: 获取当前插件在【插件管理】中设置的参数
             调用: get_argv_key(key)   
                   --> key                 插件配置参数中的键 (str/unicode)
             返回: 成功返回str,失败返回False
             """               
            if not isinstance(key, basestring):
                raise Exception("client.get_argv_key argv error, there must be (str/unicode)")
            
            return _client.get_argv_key(key)	

        @staticmethod
        def get_sys_key(key):	
            u"""
             描述: 获取系统参数
             调用: get_sys_key(key)   
                  --> key                   键 (str/unicode)
             返回: 成功返回str, 失败返回Falase
             """              
            if not isinstance(key, basestring):
                raise Exception("client.get_sys_key argv error, there must be (str/unicode)")       
            
            return _client.get_sys_key(key)
        
        @staticmethod
        def get_database():
            u"""
             描述: 获取当前项目的数据库名
             调用: get_database()   
             返回: 成功返回str,失败返回False
             """                
            return _client.get_database()
        
        @staticmethod
        def get_id():
            u"""
             描述: 获取当前主界面选择的id列表
             调用: get_id()   
             返回: 成功返回list,失败返回False
             """               
            return _client.get_id()
        
        @staticmethod
        def get_link_id():
            u"""
             描述: 获取link界面选择的id列表
             调用: get_link_id()   
             返回: 成功返回list,失败返回False
            """               
            return _client.get_link_id()
        
        @staticmethod
        def get_link_module():
            u"""
             描述: 获取link界面的模块
             调用: get_link_module()   
             返回: 成功返回str,失败返回False
            """               
            return _client.get_link_module()
        
        @staticmethod
        def get_module():
            u"""
             描述: 获取当前模块标识
             调用: get_module()   
             返回: 成功返回str,失败返回False
             """                 
            return _client.get_module()
        
        @staticmethod
        def get_module_type():
            u"""
             描述: 获取当前模块类型
             调用: get_module_type()   
             返回: 成功返回str,失败返回False
             """              
            return _client.get_module_type()
        
        @staticmethod
        def get_file():
            u"""
             描述: 获取拖入到文件框的源文件路径.仅适用于文件框菜单插件,文件框事件触发器.
             调用: get_file()   
             返回: 成功返回list,失败返回False
             """  
            return _client.get_file()
        @staticmethod
        def get_filebox_id():
            u"""
             描述: 获取文件框id.仅适用于文件框菜单插件,文件框事件触发器.
             调用: get_filebox_id()   
             返回: 成功返回str,失败返回False
             """               
            return _client.get_filebox_id()  
        @staticmethod
        def get_event_action():
            u"""
             描述: 获取数据事件触发的类型(create/update/delete).
             调用: get_event_action()   
             返回: 成功返回str,失败返回False
             """               
            return _client.get_event_action()            
        @staticmethod
        def get_event_fields():
            u"""
             描述: 获取数据事件触发时,操作的字段列表
             调用: get_event_fields()   
             返回: 成功返回list
             """               
            return _client.get_event_fields()              
                        
        @staticmethod
        def open_qc_widget(db, module, task_id, node_data_dict):
            u"""
            描述:发送给qt的界面弹出approve或者retake的界面
            调用:open_qc_widget(db, module, task_id, node_data_dict)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> module_type            模块类型 (str/unicode)
                 --> task_id                任务ID (str/unicode)
                 --> node_data_dict         节点的数据，用于更改流程
            返回:bool       
            """
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(task_id, (basestring,list)) or not isinstance(node_data_dict, dict):
                raise Exception("client.open_qc_widget argv error ,there must be (str/unicode, str/unicode, str/unicode/list, dict)")
            task_id = task_id if isinstance(task_id,list) else [task_id]
            return tw.send_local_http(db, module, "send_to_qc_widget",  {"node_data":[node_data_dict], "task_id_list":task_id, "module_type":"task"}, "get")
        
        @staticmethod
        def refresh_all(db, module, module_type, websocket_key=""):
            """
            描述:刷新客户端项目界面
            调用:refresh_all(db, module, module_type)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> module_type            模块类型 (str/unicode), 值为:info/task
            返回:bool       
            """            
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring):
                raise Exception("client.refresh_all argv error ,there must be (str/unicode, str/unicode, str/unicode)")
            
            if websocket_key=="":
                websocket_key = db
            return tw.send_local_socket("http_server", "refresh_main", {"db": db, "module":module, "module_type":module_type, "websocket_key": websocket_key}, "send")
        
        @staticmethod
        def refresh_id(db, module, module_type, id_list, filebox_id="", websocket_key=""):
            """
            描述:刷新客户端项目界面的记录
            调用:refresh_id(db, module, module_type, id_list, filebox_id="")
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> module_type            模块类型 (str/unicode), 值为:info/task
                 --> id_list                ID列表 (list)
                 --> filebox_id             文件框ID
            返回:bool       
            """            
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or not isinstance(id_list, list) or not isinstance(filebox_id, basestring):
                raise Exception("client.refresh_id argv error ,there must be (str/unicode, str/unicode, str/unicode, list)")
            
            if websocket_key=="":
                websocket_key = db
            return tw.send_local_socket("http_server", "refresh_main_recorder", {"db": db, "module":module, "module_type":module_type, "id_list":id_list, "filebox_id": filebox_id, "websocket_key": websocket_key}, "send")
    
    class login:
        
        @staticmethod
        def _login(http_ip='', account='', password='', token=''):
            global G_tw_token
            global G_tw_http_ip
            #global G_is_login
            global G_tw_file_key
            global G_tw_account_id
            global G_tw_account
            global G_bin_path
            global G_tw_proxy
            global G_tw_init_data #初始化数据
            global G_tw_api_key
            G_tw_init_data = {"http_ip":http_ip, "account":account, "password":password, "token":token}
            #是否使用系统代理---------
            t_is_use_system_proxy=False
            t_proxy_dict={}
            try:
                t_share_client=False
                sys_config_path=G_bin_path + "/cgtw/config.ini"
                if os.path.exists(sys_config_path):
                    import six.moves.configparser as configparser
                    config = configparser.ConfigParser(allow_no_value=True)
                    config.optionxform = str
                    config.read(sys_config_path)
                    try:
                        if config.has_option("General", "share_client") and config.get("General", "share_client").lower().strip() == "y":
                            t_share_client =True
                            user_config_path=os.path.join(_lib.get_app_config_dir(t_share_client), "config.ini").replace("\\", "/")
                            config = configparser.ConfigParser(allow_no_value=True)
                            config.optionxform = str
                            config.read(user_config_path)
                            ctlib.log.log_dir = os.path.join(_lib.get_app_config_dir(t_share_client), "api_log", py_dict[py_ver])  # 重定向log目录到用户目录中
                    except:
                        pass


                    if config.has_option("General", "socket_server_port"):
                        try:
                            t_socket_port = config.getint("General", "socket_server_port")
                            _con_local.socket_server_port = t_socket_port #设置本地socketserver的端口
                        except:
                            pass
                    if config.has_option("General", "http_server_port"):
                        try:
                            t_http_port = config.getint("General", "http_server_port")
                            _con_local.http_server_port = t_http_port #设置本地socketserver的端口
                        except:
                            pass

                    if config.has_option("General", "system_proxy"):
                        t_is_use_system_proxy = config.get("General","system_proxy").strip().lower() == "y"

                    if config.has_option("General", "proxy"):
                        try:
                            proxy_data = json.loads(config.get("General", "proxy"))
                            if isinstance(proxy_data, basestring):
                                proxy_data = json.loads(proxy_data)
                            if isinstance(proxy_data, dict) and {"type", "address", "port", "username", "password"} <= set(proxy_data):
                                proxy_type = proxy_data["type"]
                                proxy_address = proxy_data["address"]
                                proxy_port = proxy_data["port"]
                                proxy_username = proxy_data["username"]
                                proxy_password = proxy_data["password"]

                                if proxy_data["username"] != "" and proxy_data["password"] != "":
                                    proxy_url = "{}://{}:{}@{}:{}".format(
                                        proxy_type,
                                        proxy_username,
                                        proxy_password,
                                        proxy_address,
                                        proxy_port
                                    )
                                else:
                                    proxy_url = "{}://{}:{}".format(
                                        proxy_type,
                                        proxy_address,
                                        proxy_port
                                    )
                                t_proxy_dict['https'] = proxy_url
                        except:
                            pass

                    # 加载用户自定义的环境变量
                    if config.has_section("Environs"):
                        environs = config.items("Environs")
                        for key, value in environs:
                            try:
                                os.environ[key] = str(value)
                            except:
                                pass

            except:
                pass

            
            if len(G_tw_proxy)==0:
                if not t_is_use_system_proxy:
                    G_cgtw_session.trust_env=False#禁止系统代理
                    os.environ["NO_PROXY"] = "*"
                else:
                    G_tw_proxy=t_proxy_dict
                    for key, value in G_tw_proxy.items():
                        os.environ[key.upper() + "_PROXY"] = value
            else:
                for key, value in G_tw_proxy.items():
                    os.environ[str(key).upper()] = str(value)
                

            if to_unicode(http_ip).strip()!="" and to_unicode(account).strip()!="":
                #设置代理数据---------------
                # if t_is_use_system_proxy:
                #     from twlib._proxy import _proxy
                #     _proxy.set_proxy(G_cgtw_session, http_ip, G_bin_path)
                #设置代理数据---------------

                G_tw_http_ip=_con.get_server_ip(G_cgtw_session, http_ip)#这个中间有用session去取数据，所以在前面要先设置代理
                try:
                    machine_key = ctlib.machine().get_key()
                except:
                    machine_key = ""
                t_login_data=tw.send_web("account", "login", {"account":account, "password":password, "machine_key": machine_key})
                if t_login_data==False or not isinstance(t_login_data, dict):
                    raise Exception("tw.Login fail")

                #判断是否启用授权验证,用authorize_uuid判断--20191206
                if isinstance(t_login_data, dict) and "authorize_uuid" in t_login_data:
                    t_login_data = tw.send_web("account", "authorize", {"uuid":t_login_data["authorize_uuid"], "check_machine_key":ctlib.machine().get_check_key(t_login_data["authorize_uuid"])})
                    if t_login_data==False or not isinstance(t_login_data, dict):
                        raise Exception("tw.authorize fail")

                #判断是否启用TOTP验证---20240520
                if isinstance(t_login_data, dict) and "check_totp" in t_login_data and  t_login_data["check_totp"]=="Y" and "account_id" in t_login_data:
                    global G_tw_totp_password #初始化数据
                    t_login_data = tw.send_web("account", "totp_verify", {"account_id":t_login_data["account_id"], "totp_password":G_tw_totp_password})
                    if t_login_data==False or not isinstance(t_login_data, dict):
                        raise Exception("tw.totp_verify fail")

                G_tw_token=t_login_data["token"]
                G_tw_account_id=t_login_data["account_id"]
                G_tw_account=t_login_data["account"]
                G_tw_file_key=t_login_data["file_key"]

            elif to_unicode(http_ip).strip()!="" and to_unicode(token).strip()!="": #用token登录
                if to_unicode(G_tw_api_key).strip()=="":
                    raise Exception("tw.authorize the api_key can't empty")
                
                G_tw_http_ip =_con.get_server_ip(G_cgtw_session, http_ip)#这个中间有用session去取数据，所以在前面要先设置代理
                G_tw_token = token
                t_login_data=tw.send_web("token", "get_account_data", {})             
                if not isinstance(t_login_data, dict):
                    raise Exception("tw.Login, get account data error")       
                G_tw_account_id=t_login_data["account_id"]
                G_tw_account=t_login_data["account"]

            else:
                if G_tw_http_ip=="" or G_tw_token=="":
                    t_login_data=tw.send_local_socket("main_widget", "get_login_data", {}, "get")
                    if isinstance(t_login_data, dict) and  {"token", "account_id", "account", "server_http"}<=set(t_login_data):
                        G_tw_token=t_login_data["token"]
                        G_tw_account_id=t_login_data["account_id"]
                        G_tw_account=t_login_data["account"]
                        G_tw_http_ip=t_login_data["server_http"]


                    #设置代理数据---------------
                    # if t_is_use_system_proxy:
                    #     from twlib._proxy import _proxy
                    #     _proxy.set_proxy(G_cgtw_session, G_tw_http_ip, G_bin_path)
                    #设置代理数据---------------
       
            
        @staticmethod
        def account():
            u"""
            描述: 获取当前登录用户的账号
            调用: account()   
            返回: 成功返回str
            """              
            global G_tw_account
            global G_tw_token
            if tw.login.is_login()==False:
                return ""
            #return tw.send_web("token", "get_account", {"token":G_tw_token})
            return G_tw_account

        @staticmethod
        def account_id():
            u"""
            描述: 获取当前登录用户的ID
            调用: account_id()   
            返回: 成功返回str
            """                 
            global G_tw_account_id	
            global G_tw_token
            if tw.login.is_login()==False:
                return ""
            #return tw.send_web("c_token", "get_account_id", {"token":G_tw_token})
            return G_tw_account_id

        @staticmethod
        def token():
            u"""
            描述: 获取当前登录用户的token
            调用: token()   
            返回: 成功返回str
            """               
            global G_tw_token
            return G_tw_token


        @staticmethod
        def http_server_ip():
            u"""
            描述: 获取当前登录CGTeamwork服务器的IP和端口
            调用: http_server_ip()   
            返回: 成功返回str
            """  
            global G_tw_http_ip
            return G_tw_http_ip
        @staticmethod
        def is_login():
            u"""
            描述: 获取当前登录的状态
            调用: is_login()   
            返回: 返回bool
            """               
            global G_tw_token
            if G_tw_token=="":
                return False
            return True
    
    class status:

        @staticmethod
        def get_status_and_color():
            u"""
            描述: 获取所有状态的名称和颜色
            调用: get_status_and_color()
            返回: 成功返回dict
            """            
            return tw.send_web("status",  "get_status_and_color", {})
    
    class account:
        
        @staticmethod
        def fields():
            u"""
            描述: 获取所有字段标识
            调用: fields()
            返回: 成功返回list
            """        
            return tw.send_web(tw.account.__name__, "fields", {})
        
        @staticmethod
        def fields_and_str():
            u"""
            描述: 获取所有字段标识和中文名
            调用: fields_and_str()
            返回: 成功返回list
            """     
            return tw.send_web(tw.account.__name__, "fields_and_str", {})
        
                
        @staticmethod
        def get_id(filter_list, limit="5000", start_num=""):
            u"""
            描述: 获取记录id列表
            调用: get_id(filter_list, limit="5000", start_num="")
                 --> filter_list             过滤语句列表 (list)
                 --> limit                   限制条数 (str/unicode), 默认是5000
                 --> start_num               开始条数 (str/unicode), 默认为""
            返回: 成功返回list
            """       
            if not isinstance(filter_list, list) or not isinstance(limit, basestring) or not isinstance(start_num, basestring):
                raise Exception("account.get_id argv error, there must be(list, str/unicode, str/unicode)")       
            return tw.send_web(tw.account.__name__, "get_id", {"sign_filter_array":filter_list, "limit":limit, "start_num":start_num})
                            
        @staticmethod
        def get(id_list, field_sign_list, limit="5000", order_sign_list=[]):
            u"""
            描述: 获取记录列表
            调用: get(id_list, field_sign_list, limit="5000", order_sign_list=[])
                 --> id_list                ID列表 (list)(最大长度20000)
                 --> field_sign_list        字段标识列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_sign_list        顺序的字段标识列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(id_list, list) or not isinstance(field_sign_list, list)  or not isinstance(limit, basestring) or not isinstance(order_sign_list, list):
                raise Exception("account.get argv error, there must be(list, list, str/unicode, list)")   
            
            return tw.send_web(tw.account.__name__, "get", {"sign_array":field_sign_list, "id_array":id_list, "order_sign_array":order_sign_list, "limit":limit})
            
        @staticmethod
        def get_filter(field_sign_list, filter_list, limit="5000", order_sign_list=[], start_num=""):
            u"""
            描述: 获取记录列表
            调用: get_filter(field_sign_list, filter_list, limit="5000", order_sign_list=[], start_num="")
                 --> field_sign_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_sign_list        顺序的字段标识列表 (list)
                 --> start_num               开始条数 (str/unicode), 默认为""
                 
            返回: 成功返回list
            """              
            if not isinstance(field_sign_list, list) or not isinstance(filter_list, list)  or not isinstance(limit, basestring) or not isinstance(order_sign_list, list) or not isinstance(start_num, basestring):
                raise Exception("account.get_filter argv error, there must be(list, list, str/unicode, list, str)")   
            
            return tw.send_web(tw.account.__name__, "get_filter", {"sign_array":field_sign_list, "sign_filter_array":filter_list, "order_sign_array":order_sign_list, "limit":limit, "start_num":start_num})
        
        
        @staticmethod
        def set(id_list, sign_data_dict):
            u"""
            描述: 更新记录
            调用: set(id_list, sign_data_dict)
                 --> id_list                ID列表 (list)
                 --> sign_data_dict         更新的数据(dict), 格式:{"字段标识" : "值", "字段标识" : "值" }
            返回: 成功返回True
            """                
            if not isinstance(id_list, list) or not isinstance(sign_data_dict, dict):
                raise Exception("account.set argv error, there must be(list, dict)")                
            return tw.send_web(tw.account.__name__, "set", {"id_array":id_list, "sign_data_array":sign_data_dict})
        @staticmethod
        def count(filter_list):
            u"""
             描述: 统计记录条数
             调用: count(filter_list)
                  --> filter_list           过滤语句列表 (list)
             返回: 成功返回str
             """              
            if not isinstance(filter_list, list):
                raise Exception("account.count argv error, there must be(list)")
            return tw.send_web(tw.account.__name__, "count", {"sign_filter_array":filter_list})
        
        @staticmethod
        def distinct(filter_list, field_sign, order_sign_list=[]):
            u"""
             描述: 获取去重后的记录列表
             调用: distinct(filter_list, field_sign, order_sign_list=[])
                  --> filter_list           过滤语句列表 (list)
                  --> field_sign            字段标识 (str/unicode)
                  --> order_sign_list       排序列表 (list)
             返回: 成功返回list
             """               
            if not isinstance(filter_list, list) or not isinstance(field_sign, basestring) or not isinstance(order_sign_list, list):
                raise Exception("account.distinct argv error, there must be(list, str/unicode, list)")     
            return tw.send_web(tw.account.__name__, "distinct", {"distinct_sign":field_sign ,"sign_filter_array":filter_list, "order_sign_array":order_sign_list})

        @staticmethod
        def group_count(field_sign_list, filter_list):
            u"""
             描述: 按字段标识进行分组统计条数
             调用: group_count(field_sign_list, filter_list)
                  --> field_sign_list       字段标识列表 (list)
                  --> filter_list           过滤语句列表 (list)
             返回: 成功返回list
             """             
            if not isinstance(field_sign_list, list) or not isinstance(filter_list, list) :
                raise Exception("account.group_count argv error, there must be(list, list)")  
            return tw.send_web(tw.account.__name__, "group_count", {"sign_array":field_sign_list, "sign_filter_array":filter_list})
    
    class project:
        
        @staticmethod
        def fields():
            u"""
            描述: 获取所有字段标识
            调用: fields()
            返回: 成功返回list
            """        
            return tw.send_web(tw.project.__name__, "fields", {})
        
        @staticmethod
        def fields_and_str():
            u"""
            描述: 获取所有字段标识和中文名
            调用: fields_and_str()
            返回: 成功返回list
            """     
            return tw.send_web(tw.project.__name__, "fields_and_str", {})
        
                
        @staticmethod
        def get_id(filter_list, limit="5000", start_num=""):
            u"""
            描述: 获取记录id列表
            调用: get_id(filter_list, limit="5000", start_num="")
                 --> filter_list             过滤语句列表 (list)
                 --> limit                   限制条数 (str/unicode), 默认是5000
                 --> start_num               开始条数 (str/unicode), 默认为""
            返回: 成功返回list
            """       
            if not isinstance(filter_list, list) or not isinstance(limit, basestring) or not isinstance(start_num, basestring):
                raise Exception("project.get_id argv error, there must be(list, str/unicode, str/unicode)")       
            return tw.send_web(tw.project.__name__, "get_id", {"sign_filter_array":filter_list, "limit":limit, "start_num":start_num})
                            
        @staticmethod
        def get(id_list, field_sign_list, limit="5000", order_sign_list=[]):
            u"""
            描述: 获取记录列表
            调用: get(id_list, field_sign_list, limit="5000", order_sign_list=[])
                 --> id_list                ID列表 (list)(最大长度20000)
                 --> field_sign_list        字段标识列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_sign_list        顺序的字段标识列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(id_list, list) or not isinstance(field_sign_list, list)  or not isinstance(limit, basestring) or not isinstance(order_sign_list, list):
                raise Exception("project.get argv error, there must be(list, list, str/unicode, list)")   
            
            return tw.send_web(tw.project.__name__, "get", {"sign_array":field_sign_list, "id_array":id_list, "order_sign_array":order_sign_list, "limit":limit})
            
        @staticmethod
        def get_filter(field_sign_list, filter_list, limit="5000", order_sign_list=[], start_num=""):
            u"""
            描述: 获取记录列表
            调用: get_filter(field_sign_list, filter_list, limit="5000", order_sign_list=[], start_num="")
                 --> field_sign_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_sign_list        顺序的字段标识列表 (list)
                 --> start_num               开始条数 (str/unicode), 默认为""
                 
            返回: 成功返回list
            """              
            if not isinstance(field_sign_list, list) or not isinstance(filter_list, list)  or not isinstance(limit, basestring) or not isinstance(order_sign_list, list) or not isinstance(start_num, basestring):
                raise Exception("project.get_filter argv error, there must be(list, list, str/unicode, list, str)")   
            
            return tw.send_web(tw.project.__name__, "get_filter", {"sign_array":field_sign_list, "sign_filter_array":filter_list, "order_sign_array":order_sign_list, "limit":limit, "start_num":start_num})


        @staticmethod
        def set(id_list, sign_data_dict):
            u"""
            描述: 更新记录
            调用: set(id_list, sign_data_dict)
                 --> id_list                ID列表 (list)
                 --> sign_data_dict         更新的数据(dict), 格式:{"字段标识" : "值", "字段标识" : "值" }
            返回: 成功返回True
            """                
            if not isinstance(id_list, list) or not isinstance(sign_data_dict, dict):
                raise Exception("project.set argv error, there must be(list, dict)")                
            return tw.send_web(tw.project.__name__, "set", {"id_array":id_list, "sign_data_array":sign_data_dict})


        @staticmethod
        def count(filter_list):
            u"""
             描述: 统计记录条数
             调用: count(filter_list)
                  --> filter_list           过滤语句列表 (list)
             返回: 成功返回str
             """              
            if not isinstance(filter_list, list):
                raise Exception("project.count argv error, there must be(list)")
            return tw.send_web(tw.project.__name__, "count", {"sign_filter_array":filter_list})
        
        @staticmethod
        def distinct(filter_list, field_sign, order_sign_list=[]):
            u"""
             描述: 获取去重后的记录列表
             调用: distinct(filter_list, field_sign, order_sign_list=[])
                  --> filter_list           过滤语句列表 (list)
                  --> field_sign            字段标识 (str/unicode)
                  --> order_sign_list       排序列表 (list)
             返回: 成功返回list
             """               
            if not isinstance(filter_list, list) or not isinstance(field_sign, basestring) or not isinstance(order_sign_list, list):
                raise Exception("project.distinct argv error, there must be(list, str/unicode, list)")     
            return tw.send_web(tw.project.__name__, "distinct", {"distinct_sign":field_sign ,"sign_filter_array":filter_list, "order_sign_array":order_sign_list})

        @staticmethod
        def group_count(field_sign_list, filter_list):
            u"""
             描述: 按字段标识进行分组统计条数
             调用: group_count(field_sign_list, filter_list)
                  --> field_sign_list       字段标识列表 (list)
                  --> filter_list           过滤语句列表 (list)
             返回: 成功返回list
             """             
            if not isinstance(field_sign_list, list) or not isinstance(filter_list, list) :
                raise Exception("project.group_count argv error, there must be(list, list)")  
            return tw.send_web(tw.project.__name__, "group_count", {"sign_array":field_sign_list, "sign_filter_array":filter_list})
    
    class info:
        __module_type="info"
        
        @staticmethod
        def modules(db):
            u"""
            描述: 获取所有模块
            调用: modules(db)
                  --> db                      数据库 (str/unicode)
            返回: 成功返回list
            """             
            if not isinstance(db, basestring):
                raise Exception("info.modules argv error, there must be (str/unicode)")     
            return tw.send_web(tw.info.__name__, "modules", {"db":db})
        
        @staticmethod
        def fields(db, module):
            u"""
            描述: 获取所有字段标识
            调用: fields(db, module)
                  --> db                    数据库 (str/unicode)
                  --> module                模块 (str/unicode)
            返回: 成功返回list
            """      
            if not isinstance(db, basestring) or not isinstance(module, basestring) :
                raise Exception("info.fields argv error, there must be(str/unicode, str/unicode)")     
            return tw.send_web(tw.info.__name__, "fields", {"db":db, "module":module})
        
        @staticmethod
        def fields_and_str(db, module):
            u"""
            描述: 获取所有字段标识和中文名
            调用: fields_and_str(db, module)
                  --> db                    数据库 (str/unicode)
                  --> module                模块 (str/unicode)
            返回: 成功返回list
            """     
            if not isinstance(db, basestring) or not isinstance(module, basestring) :
                raise Exception("info.fields_and_str argv error, there must be(str/unicode, str/unicode)")                
            return tw.send_web(tw.info.__name__, "fields_and_str", {"db":db, "module":module})
        
                
        @staticmethod
        def get_id(db, module, filter_list, limit="5000", start_num=""):
            u"""
            描述: 获取记录id列表
            调用: get_id(db, module, filter_list, limit="5000", start_num="")
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> filter_list             过滤语句列表 (list)
                 --> limit                   限制条数 (str/unicode), 默认是5000
                 --> start_num               开始条数 (str/unicode), 默认为""
            返回: 成功返回list
            """       
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(filter_list, list) or \
               not isinstance(limit, basestring) or not isinstance(start_num, basestring):
                raise Exception("info.get_id argv error, there must be(str/unicode, str/unicode, list, str/unicode, str/unicode)")       
            return tw.send_web(tw.info.__name__, "get_id", {"db":db, "module":module, "sign_filter_array":filter_list, "limit":limit, "start_num":start_num})
                            
        @staticmethod
        def get(db, module, id_list, field_sign_list, limit="5000", order_sign_list=[]):
            u"""
            描述: 获取记录列表
            调用: get(db, module, id_list, field_sign_list, limit="5000", order_sign_list=[])
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)(最大长度20000)
                 --> field_sign_list        字段标识列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_sign_list        顺序的字段标识列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
               not isinstance(field_sign_list, list)  or not isinstance(limit, basestring) or not isinstance(order_sign_list, list):
                raise Exception("info.get argv error, there must be(str/unicode, str/unicode, list, list, str/unicode, list)")   
            
            return _module.get(tw.send_web, db, module, tw.info.__module_type, id_list, field_sign_list, limit, order_sign_list) 
        
        @staticmethod
        def get_filter(db, module, field_sign_list, filter_list, limit="5000", order_sign_list=[], start_num=""):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, module, field_sign_list, filter_list, limit="5000", order_sign_list=[], start_num="")
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> field_sign_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_sign_list        顺序的字段标识列表 (list)
                 --> start_num               开始条数 (str/unicode), 默认为""
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(field_sign_list, list) or not isinstance(filter_list, list)  or not isinstance(limit, basestring) or not isinstance(order_sign_list, list) or not isinstance(start_num, basestring):
                raise Exception("info.get_filter argv error, there must be(str/unicode, str/unicode, list, list, str/unicode, list, str)")   
            
            return tw.send_web(tw.info.__name__, "get_filter", {"db":db, "module":module, "sign_array":field_sign_list, "sign_filter_array":filter_list, "order_sign_array":order_sign_list, "limit":limit, "start_num":start_num})
        
        
        @staticmethod
        def get_dir(db, module, id_list, folder_sign_list):
            u"""
            描述: 用目录标识列表获取对应的目录列表
            调用: get_dir(db, module, id_list, folder_sign_list)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> folder_sign_list       目录标识列表 (list)

            返回: 成功返回list
            """     
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
               not isinstance(folder_sign_list, list) :
                raise Exception("info.get_dir argv error, there must be(str/unicode, str/unicode, list, list)")   

            return tw.send_web(tw.info.__name__, "get_dir", {"db":db, "module":module, "sign_array":folder_sign_list, "id_array":id_list, "os":_lib.get_os()})
        
        @staticmethod
        def get_field_and_dir(db, module, id_list, field_sign_list, folder_sign_list):
            u"""
            描述: 用目录标识列表和字段标识列表获取对应的目录和字段列表
            调用: get_field_and_dir(db, module, id_list, field_sign_list, folder_sign_list)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign_list        字段标识列表 (list)
                 --> folder_sign_list       目录标识列表 (list)

            返回: 成功返回list
            """       
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
                       not isinstance(field_sign_list, list) or not isinstance(folder_sign_list, list):
                raise Exception("info.get_field_and_dir argv error, there must be(str/unicode, str/unicode, list, list, list)")      
            return tw.send_web(tw.info.__name__, "get_field_and_dir", {"db":db, "module":module, "field_sign_array":field_sign_list, "folder_sign_array":folder_sign_list,"id_array":id_list, "os":_lib.get_os()})
        
        @staticmethod
        def get_makedirs(db, module, id_list):      
            u"""
            描述:获取创建目录的列表
            调用:get_makedirs(db, module, id_list)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
            返回: 成功返回list
             """            
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list):
                raise Exception("info.get_makedirs argv error, there must be(str/unicode, str/unicode, list)")               
            return _module.get_makedirs(tw.send_web, db, module, tw.info.__module_type, id_list)
        
        @staticmethod
        def get_sign_filebox(db, module, id, filebox_sign):
            u"""
            描述: 根据文件框标识获取文件框设置信息
            调用: get_sign_filebox(db, module, id, filebox_sign)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id                     ID (str/unicode)
                 --> filebox_sign           文件框标识 (str/unicode)
            返回: 成功返回dict
            """    
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id, basestring) or \
               not isinstance(filebox_sign, basestring):
                raise Exception("info.get_sign_filebox argv error, there must be(str/unicode, str/unicode, str/unicode, str/unicode)")     
            return tw.send_web(tw.info.__name__, "get_sign_filebox", {"db":db, "module":module,  "id":id, "os":_lib.get_os(), "filebox_sign":filebox_sign})
        
        @staticmethod
        def get_filebox(db, module, id, filebox_id):
            u"""
            描述: 获取文件框设置信息
            调用: get_filebox(db, module, id, filebox_id)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id                     ID (str/unicode)
                 --> filebox_id             文件框ID (str/unicode)
            返回: 成功返回dict
            """          
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id, basestring) or \
               not isinstance(filebox_id, basestring):
                raise Exception("info.get_filebox argv error, there must be(str/unicode, str/unicode, str/unicode, str/unicode)")   
            return tw.send_web(tw.info.__name__, "get_filebox", {"db":db, "module":module,  "id":id, "os":_lib.get_os(), "filebox_id":filebox_id})

        @staticmethod
        def set(db, module, id_list, sign_data_dict, exec_event_filter=True):
            u"""
            描述: 更新记录
            调用: set(db, module, id_list, sign_data_dict, exec_event_filter=True)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> sign_data_dict         更新的数据(dict), 格式:{"字段标识" : "值", "字段标识" : "值" }
                 --> exec_event_filter       执行事件过滤器(bool)
            返回: 成功返回True
            """                
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
               not isinstance(sign_data_dict, dict) or not isinstance(exec_event_filter, bool):
                raise Exception("info.set argv error, there must be(str/unicode, str/unicode, list, dict, bool)")                
            return _module.set(tw.send_web, db, module, tw.info.__module_type, id_list, sign_data_dict, exec_event_filter)

        @staticmethod
        def delete(db, module, id_list, exec_event_filter=True):
            u"""
            描述: 删除记录
            调用: delete(db, module, id_list)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> exec_event_filter       执行事件过滤器(bool)
            返回: 成功返回True
            """
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or not isinstance(exec_event_filter, bool):
                raise Exception("info.delete argv error, there must be(str/unicode, str/unicode, list, bool)")     
            return tw.send_web(tw.info.__name__, "delete", {"db":db, "module":module,  "id_array":id_list, "exec_event_filter":exec_event_filter})
        
        @staticmethod
        def create(db, module, sign_data_dict, exec_event_filter=True, argv_dict={}):
            u"""
            描述: 创建记录
            调用: create(db, module, sign_data_dict, exec_event_filter=True, argv_dict={})
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> sign_data_dict         创建的数据 (dict), 格式:{字段标识1: 值1, 字段标识2: 值2, 字段标识3:值3}
                                            目前支持自定义信息ID. 例如:{module+'.id':'1234abcd'}
                 --> exec_event_filter      执行事件过滤器(bool)
                 --> argv_dict              其他参数(dict)

            返回: 成功返回id
            """          
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(sign_data_dict, dict) or not isinstance(exec_event_filter, bool) or not isinstance(argv_dict,dict):
                raise Exception("info.create argv error, there must be(str/unicode, str/unicode, dict, bool, dict)")
            
            #2022--#检查唯一值
            check_unique = argv_dict.get("check_unique", False) 
            if not isinstance(check_unique, bool):
                raise Exception("info.create, the check_unique value error, is bool")

            return tw.send_web(tw.info.__name__, "create", {"db":db, "module":module, "sign_data_array":sign_data_dict, "exec_event_filter":exec_event_filter, "check_unique":check_unique})

        @staticmethod
        def download_image(db, module, id_list, field_sign, is_small=True, local_dir=""):
            u"""
            描述: 下载图片字段的图片
            调用: download_image(db, module, id_list, field_sign, is_small=True, local_dir="")
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign             图片字段标识 (str/unicode)
                 --> is_small               是否下载小图 (bool), 默认为True
                 --> local_dir              指定路径 (unicode), 默认为temp路径
            返回: 成功返回list
            """                
            global G_tw_http_ip
            global G_tw_token
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
                       not isinstance(field_sign, basestring) or not isinstance(is_small, bool) or not isinstance(local_dir, basestring):
                raise Exception("info.download_image argv error, there must be(str/unicode, str/unicode, list,  str/unicode, bool, unicode)") 
            
            return _module.download_image(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.info.__module_type, id_list, field_sign, is_small, local_dir)
        
        @staticmethod
        def set_image(db, module, id_list, field_sign, img_path, compress="1080", exec_event_filter=True):
            u"""
             描述: 更新图片字段的图片
             调用: set_image(db, module, id_list, field_sign, img_path, compress="1080", exec_event_filter=True)
                  --> db                    数据库 (str/unicode)
                  --> module                模块 (str/unicode)
                  --> id_list               ID列表 (list)
                  --> field_sign            图片字段标识 (str/unicode)
                  --> img_path              图片路径 (str/unicode/list)
                  --> compress              压缩比例 (str/unicode), 可选值 no_compress(无压), 1080(1920x1080), 720(1280x720), 540(960x540)
                  --> exec_event_filter     执行事件过滤器(bool)
             返回: 成功返回True
             """                 
            global G_tw_http_ip
            global G_tw_token
            
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
                       not isinstance(field_sign, basestring) or not isinstance(img_path, (basestring, list)) or not isinstance(compress, basestring) or not isinstance(exec_event_filter, bool):
                raise Exception("info.set_image argv error, there must be(str/unicode, str/unicode, list, str/unicode, str/unicode/list, str/unicode, bool)")             
            return _module.set_image(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.info.__module_type, id_list, field_sign, img_path, compress, exec_event_filter)

        @staticmethod
        def count(db, module, filter_list):
            u"""
             描述: 统计记录条数
             调用: count(db, module, filter_list)
                  --> db                    数据库 (str/unicode)
                  --> module                模块 (str/unicode)
                  --> filter_list           过滤语句列表 (list)
             返回: 成功返回str
             """              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(filter_list, list):
                raise Exception("info.count argv error, there must be(str/unicode, str/unicode, list)")
            return tw.send_web(tw.info.__name__, "count", {"db":db, "module":module,  "sign_filter_array":filter_list})
        
        @staticmethod
        def distinct(db, module, filter_list, field_sign, order_sign_list=[]):
            u"""
             描述: 获取去重后的记录列表
             调用: distinct(db, module, filter_list, field_sign, order_sign_list=[])
                  --> db                    数据库 (str/unicode)
                  --> module                模块 (str/unicode)
                  --> filter_list           过滤语句列表 (list)
                  --> field_sign            字段标识 (str/unicode)
                  --> order_sign_list       排序列表 (list)
             返回: 成功返回list
             """               
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(filter_list, list) or \
               not isinstance(field_sign, basestring) or not isinstance(order_sign_list, list):
                raise Exception("info.distinct argv error, there must be(str/unicode, str/unicode, list, str/unicode, list)")     
            return tw.send_web(tw.info.__name__, "distinct", {"db":db, "module":module, "distinct_sign":field_sign ,"sign_filter_array":filter_list, "order_sign_array":order_sign_list})

        @staticmethod
        def group_count(db, module, field_sign_list, filter_list):
            u"""
             描述: 按字段标识进行分组统计条数
             调用: group_count(db, module, field_sign_list, filter_list)
                  --> db                    数据库 (str/unicode)
                  --> module                模块 (str/unicode)
                  --> field_sign_list       字段标识列表 (list)
                  --> filter_list           过滤语句列表 (list)
             返回: 成功返回list
             """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(field_sign_list, list) or \
                       not isinstance(filter_list, list) :
                raise Exception("info.group_count argv error, there must be(str/unicode, str/unicode, list, list)")  
            return tw.send_web(tw.info.__name__, "group_count", {"db":db, "module":module, "sign_array":field_sign_list, "sign_filter_array":filter_list})
        
        @staticmethod
        def send_msg(db, module, id, account_id_list, content="", important=False):
            u"""
             描述: 给指定用户发送任务相关消息
             调用: send_msg(db, module, id, account_id_list, content="", important=False)
                   --> db                      数据库 (str/unicode)
                   --> module                  模块 (str/unicode)
                   --> id                      信息ID (str/unicode)
                   --> account_id_list         账号ID列表 (list)
                   --> content                 发送的内容 (str/unicode/list) 
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                   --> important                是否强提醒
             返回: 成功返回True
             """           
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or  not isinstance(id, basestring) or not isinstance(account_id_list, list) or \
               not isinstance(content,(list,basestring)) or not isinstance(important, bool):
                raise Exception("info.send_msg argv error ,there must be (str/unicode, str/unicode, str/unicode, str/unicode, list,  str/unicode, bool)")
            content = _dom.to_list(G_tw_http_ip, G_tw_token, db, content)
            return tw.send_web(tw.info.__name__, "send_msg", {"db":db, "module":module, "task_id":id, "account_id_array":account_id_list, "content":content, "important":important})

        @staticmethod
        def set_media(db, module, id_list, field_sign, data_list, exec_event_filter=True):
            """
            描述:更新多媒体字段
            调用:set_media(db, module, id_list, field_sign, data_list, exec_event_filter=True)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign             字段标识 (str/unicode)
                 --> data_list              文件列表['1.jpg','z:/1.mov','1.txt']  
                 ---> exec_event_filter      执行事件过滤器(bool)
            返回:成功返回True                        
            """
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or\
               not isinstance(field_sign, basestring) or not isinstance(data_list, list) or not isinstance(exec_event_filter, bool):
                raise Exception("info.set_media argv error, there must be (str/unicode, str/unicode, list, str/unicode, list, bool)")
                             
            return _module.set_media(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.info.__module_type, id_list, field_sign, data_list, exec_event_filter)

        @staticmethod
        def append_media(db, module, id_list, field_sign, data_list, a_append_after=True, exec_event_filter=True):
            """
            描述:追加多媒体字段
            调用:append_media(db, module, id_list, field_sign, data_list, a_append_after=True, exec_event_filter=True)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign             字段标识 (str/unicode)
                 --> data_list              文件列表['1.jpg','z:/1.mov','1.txt']  
                 --> append_after           默认往后追加
                 --> exec_event_filter      执行事件过滤器(bool)
            返回:成功返回True                        
            """
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or\
               not isinstance(field_sign, basestring) or not isinstance(data_list, list) or not isinstance(a_append_after, bool) or not isinstance(exec_event_filter, bool):
                raise Exception("info.append_media argv error, there must be (str/unicode, str/unicode, list, str/unicode, list, bool, bool)")
                             
            return _module.append_media(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.info.__module_type, id_list, field_sign, data_list, a_append_after, exec_event_filter)
            
        @staticmethod
        def download_media(db, module, id_list, field_sign, local_dir=''):
            """
            描述:下载多媒体字段
            调用:download_media(db, module, id_list, field_sign, local_dir="")
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign             字段标识 (str/unicode)
                 --> local_dir              保存目录,默认为temp路径     
            返回:列表       
            """
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or\
               not isinstance(field_sign, basestring) or not isinstance(local_dir, basestring):
                raise Exception("info.download_media argv error, there must be (str/unicode, str/unicode, list, str/unicode, str/unicode)")
            
            return _module.download_media(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.info.__module_type, id_list, field_sign, local_dir)
        
        @staticmethod
        def publish(db, module, id, path_list, filebox_sign, version="", version_argv={}, note="", note_argv={}, call_back=None, argv_dict={}):
            """
            描述:发布版本
            调用:publish(db, module, id, path_list, filebox_sign, version="", version_argv={}, note="", note_argv={}, call_back=None, argv_dict={})
                 ---> db                     数据库 (str/unicode)
                 ---> module                 模块 (str/unicode)
                 ---> id                     ID (str/unicode)
                 ---> path_list              本地文件列表(list)
                 ---> filebox_sign           文件框标识 (str/unicode)
                 ---> version                版本号(str/unicode),三位数,如 001, 002     
                 ---> version_argv           版本参数(dict)
                 ---> note                   内容 (str/unicode/list),默认为""
                                             list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                             [{"type":"text","content":"te"},
                                             {"type":"a","title":"aa","url":"g:/1.jpg"},
                                             {"type":"image","path":"1.jpg"},
                                             {"type":"attachment","path":"1.txt"}]
                ---> note_argv               note参数(dict)
                ---> argv_dict               其他参数(dict). 
                                                目前支持key:is_upload_follow_filebox. 当传入 is_upload_follow_filebox:False时. 不根据文件框设置走(当开启上传网盘功能时. 不会上传网盘)

            返回: 成功返回True
            """
                     
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id, basestring) or not isinstance(path_list, list) or\
               not isinstance(filebox_sign, basestring) or not isinstance(version, basestring) or not isinstance(version_argv, dict) or not isinstance(note,(list, basestring)) \
                   or not isinstance(note_argv, dict) or not isinstance(argv_dict,dict):
                raise Exception("info.publish argv error, there must be (str/unicode, str/unicode, str/unicode, list, str/unicode, str/unicode, str/unicode, dict, str/unicode/list, dict, dict)")
            
            global G_tw_http_ip
            global G_tw_token                
            note = _dom.to_list(G_tw_http_ip, G_tw_token, db, note)            
            return _module.publish(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.info.__module_type, id, path_list, filebox_sign, version, version_argv, note, note_argv, call_back, argv_dict)
    
    class task:
        __module_type="task"
        
        @staticmethod
        def modules(db):
            u"""
            描述: 获取所有启用任务的模块
            调用: modules(db)
                  --> db                    数据库 (str/unicode)
            返回: 成功返回list
            """         
            if not isinstance(db, basestring):
                raise Exception("task.modules argv error, there must be (str/unicode)")         
            return tw.send_web(tw.task.__name__, "modules", {"db":db})
        
        @staticmethod
        def fields(db, module):
            u"""
            描述: 获取所有字段标识
            调用: fields(db, module)
                  --> db                    数据库 (str/unicode)
                  --> module                模块 (str/unicode)
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(module, basestring) :
                raise Exception("task.fields argv error, there must be(str/unicode, str/unicode)")    
            return tw.send_web(tw.task.__name__, "fields", {"db":db, "module":module})
        
        @staticmethod
        def fields_and_str(db, module):
            u"""
            描述: 获取所有字段标识和中文名
            调用: fields_and_str(db, module)
                  --> db                    数据库 (str/unicode)
                  --> module                模块 (str/unicode)
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(module, basestring) :
                raise Exception("task.fields_and_str argv error, there must be(str/unicode, str/unicode)")                
            return tw.send_web(tw.task.__name__, "fields_and_str", {"db":db, "module":module})  
               
            
        @staticmethod
        def get_id(db, module, filter_list, limit="5000", start_num=""):
            u"""
            描述: 获取记录id列表
            调用: get_id(db, module, filter_list, limit="5000", start_num="")
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> start_num              起始条数 (str/unicode), 默认为""
            返回: 成功返回list
            """                  
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(filter_list, list) or \
                       not isinstance(limit, basestring) or not isinstance(start_num, basestring):
                raise Exception("task.get_id argv error, there must be(str/unicode, str/unicode, list, str/unicode, str/unicode)")                 
            return tw.send_web(tw.task.__name__, "get_id", {"db":db, "module":module, "sign_filter_array":filter_list, "limit":limit, "start_num":start_num})
                    
        @staticmethod
        def get(db, module, id_list, field_sign_list, limit="5000", order_sign_list=[]):
            u"""
            描述: 获取记录列表
            调用: get(db, module, id_list, field_sign_list, limit="5000", order_sign_list=[])
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)(最大长度20000)
                 --> field_sign_list        字段标识列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_sign_list        排序的字段标识列表 (list)
            返回: 成功返回list
            """                 
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
                       not isinstance(field_sign_list, list)  or not isinstance(limit, basestring) or not isinstance(order_sign_list, list):
                raise Exception("task.get argv error, there must be(str/unicode, str/unicode, list, list, str/unicode, list)")  
            
            return _module.get(tw.send_web, db, module, tw.task.__module_type, id_list, field_sign_list, limit, order_sign_list)       
        
        
        @staticmethod
        def get_filter(db, module, field_sign_list, filter_list, limit="5000", order_sign_list=[], start_num=""):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, module, field_sign_list, filter_list, limit="5000", order_sign_list=[], start_num="")
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> field_sign_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_sign_list        顺序的字段标识列表 (list)
                 --> start_num               开始条数 (str/unicode), 默认为""
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(field_sign_list, list) or not isinstance(filter_list, list)  or not isinstance(limit, basestring) or not isinstance(order_sign_list, list) or not isinstance(start_num, basestring):
                raise Exception("task.get_filter argv error, there must be(str/unicode, str/unicode, list, list, str/unicode, list, str)")   
            
            return tw.send_web(tw.task.__name__, "get_filter", {"db":db, "module":module, "sign_array":field_sign_list, "sign_filter_array":filter_list, "order_sign_array":order_sign_list, "limit":limit, "start_num":start_num})
               
        
        @staticmethod
        def get_dir(db, module, id_list, folder_sign_list):
            u"""
            描述: 用目录标识列表获取对应的目录列表
            调用: get_dir(db, module, id_list, folder_sign_list)
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id_list                 ID列表 (list)
                 --> folder_sign_list        目录标识列表 (list)

            返回: 成功返回list
            """            
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
                       not isinstance(folder_sign_list, list) :
                raise Exception("task.get_dir argv error, there must be(str/unicode, str/unicode, list, list)")               
            return tw.send_web(tw.task.__name__, "get_dir", {"db":db, "module":module, "sign_array":folder_sign_list, "id_array":id_list, "os":_lib.get_os()}) 
        
        @staticmethod
        def get_field_and_dir(db, module, id_list, field_sign_list, folder_sign_list):
            u"""
            描述: 用目录标识列表和字段标识列表获取对应的目录和字段列表
            调用: get_field_and_dir(db, module, id_list, field_sign_list, folder_sign_list)
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id_list                 ID列表 (list)
                 --> field_sign_list         字段标识列表 (list)
                 --> folder_sign_list        目录标识列表 (list)

            返回: 成功返回list
            """      
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
                       not isinstance(field_sign_list, list) or not isinstance(folder_sign_list, list):
                raise Exception("task.get_field_and_dir argv error, there must be(str/unicode, str/unicode, list, list, list)")               
            return tw.send_web(tw.task.__name__, "get_field_and_dir", {"db":db, "module":module, "field_sign_array":field_sign_list, "folder_sign_array":folder_sign_list,"id_array":id_list, "os":_lib.get_os()})      
                
        @staticmethod
        def get_makedirs(db, module, id_list):   
            u"""
            描述:获取创建目录的列表
            调用:get_makedirs(db, module, id_list)
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id_list                 ID列表 (list)
            返回: 成功返回list
             """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list):
                raise Exception("task.get_makedirs argv error, there must be(str/unicode, str/unicode, list)")                
            return _module.get_makedirs(tw.send_web, db, module, tw.task.__module_type, id_list)
        
        @staticmethod
        def get_submit_filebox_sign(db, module, id):
            u"""
            描述: 获取提交流程的文件框标识列表
            调用: get_submit_filebox_sign(db, module, id)
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id                      ID (str/unicode)
            返回: 成功返回list
            """                
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id, basestring):
                raise Exception("task.get_submit_filebox argv error, there must be(str/unicode, str/unicode, str/unicode, str/unicode)")             
            return tw.send_web(tw.task.__name__, "get_submit_filebox_sign", {"db":db, "module":module, "id":id}) 
                    
        @staticmethod
        def get_sign_filebox(db, module, id, filebox_sign):
            u"""
            描述: 根据文件框标识获取文件框设置信息
            调用: get_sign_filebox(db, module, id, filebox_sign)
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id                      ID (str/unicode)
                 --> filebox_sign            文件框标识 (str/unicode)
            返回: 成功返回dict
            """                  
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id, basestring) or \
                       not isinstance(filebox_sign, basestring):
                raise Exception("task.get_sign_filebox argv error, there must be(str/unicode, str/unicode, str/unicode, str/unicode)")              
            return tw.send_web(tw.task.__name__, "get_sign_filebox", {"db":db, "module":module,  "id":id, "os":_lib.get_os(), "filebox_sign":filebox_sign})
        
        @staticmethod
        def get_filebox(db, module, id, filebox_id):
            u"""
            描述: 获取文件框设置信息
            调用: get_filebox(db, module, id, filebox_id)
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id                      ID (str/unicode)
                 --> filebox_id              文件框ID (str/unicode)
            返回: 成功返回dict
            """                
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id, basestring) or \
                       not isinstance(filebox_id, basestring):
                raise Exception("task.get_filebox argv error, there must be(str/unicode, str/unicode, str/unicode, str/unicode)")              
            return tw.send_web(tw.task.__name__, "get_filebox", {"db":db, "module":module,  "id":id, "os":_lib.get_os(), "filebox_id":filebox_id})
        
        @staticmethod
        def get_review_file(db, module, id_list):
            u"""
            描述: 获取可预览最后版本文件,用于视频串播
            调用: get_review_file(db, module, id_list)
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id_list                 ID (list)
            返回: 成功返回list
            """     
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list):
                raise Exception("task.get_review_file argv error, there must be(str/unicode, str/unicode, list)")  
            
            return tw.send_web(tw.task.__name__, "get_review_file", {"db":db, "module":module, "link_id_array":id_list, "os":_lib.get_os()}) 
                
        @staticmethod
        def get_version_file(db, module, id_list, filebox_sign):
            u"""
            描述: 获取文件框最后版本文件
            调用: get_version_file(db, module, id_list, filebox_sign="review")
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id_list                 ID (list)
                 --> filebox_sign            文件框标识(str/unicode)
            返回: 成功返回list
            """     
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or not isinstance(filebox_sign, basestring) :
                raise Exception("task.get_version_file argv error, there must be(str/unicode, str/unicode, list, str/unicode)")              
            return tw.send_web(tw.task.__name__, "get_version_file", {"db":db, "module":module, "link_id_array":id_list, "filebox_sign":filebox_sign, "os":_lib.get_os()}) 
     
        
        @staticmethod
        def set(db, module, id_list, sign_data_dict, exec_event_filter=True):
            u"""
            描述: 更新记录
            调用: set(db, module, id_list, sign_data_dict, exec_event_filter=True)
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id_list                 ID (list)
                 --> sign_data_dict          更新数据 (dict), 格式:{"字段标识" : "值", "字段标识" : "值" }
                 --> exec_event_filter       执行事件过滤器(bool)
            返回: 成功返回True
            """     
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
                       not isinstance(sign_data_dict, dict ) or not isinstance(exec_event_filter, bool):
                raise Exception("task.set argv error, there must be(str/unicode, str/unicode, list, dict, bool)")              
            return _module.set(tw.send_web, db, module, tw.task.__module_type, id_list, sign_data_dict, exec_event_filter)

        @staticmethod
        def delete(db, module, id_list, exec_event_filter=True):
            u"""
            描述: 删除记录
            调用: delete(db, module, id_list)
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id_list                 ID列表 (list)
                 --> exec_event_filter       执行事件过滤器(bool)
            返回: 成功返回True
            """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or not isinstance(exec_event_filter, bool):
                raise Exception("task.delete argv error, there must be(str/unicode, str/unicode, list, bool)")        
            return tw.send_web(tw.task.__name__, "delete", {"db":db, "module":module,  "id_array":id_list, "exec_event_filter":exec_event_filter})
        
        @staticmethod
        def create(db, module, join_id, pipeline_id, task_name, flow_id, sub_pipeline_id="", pipeline_template_id="", sign_data_dict={}, exec_event_filter=True):
            u"""
            描述: 创建记录
            调用: create(db, module, join_id, pipeline_id, task_name, flow_id, sub_pipeline_id="", pipeline_template_id="")
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> join_id                 信息表的ID (str/unicode)
                 --> pipeline_id             阶段ID (str/unicode)
                 --> task_name               任务名称 (str/unicode)
                 --> flow_id                 流程ID (str/unicode)
                 --> sub_pipeline_id         子阶段ID (str/unicode)
                 --> pipeline_template_id    阶段流程ID (str/unicode)
                 --> sign_data_dict          创建的数据 (dict), 格式:{字段标识1: 值1, 字段标识2: 值2, 字段标识3:值3}
                                             目前支持自定义任务ID. 例如:{'task.id':'1234abcd'}
                --> exec_event_filter       执行事件过滤器(bool)
            返回: 成功返回ID
            """            
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(join_id, basestring) or \
               not isinstance(pipeline_id, basestring) or not isinstance(task_name, basestring) or not isinstance(flow_id, basestring) or not isinstance(sub_pipeline_id, basestring) or not isinstance(pipeline_template_id, basestring)\
                   or not isinstance(sign_data_dict,dict) or not isinstance(exec_event_filter, bool):
                raise Exception("task.create argv error, there must be(str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, dict, bool)")    
            return tw.send_web(tw.task.__name__, "create", {"db":db, "module":module, "join_id":join_id, "pipeline_id":pipeline_id, "sub_pipeline_id":sub_pipeline_id, "flow_id":flow_id, "task_name":task_name, "pipeline_template_id":pipeline_template_id, "sign_data_array":sign_data_dict,"exec_event_filter":exec_event_filter})

        @staticmethod
        def download_image(db, module, id_list, field_sign, is_small=True, local_dir=""):
            u"""
            描述: 下载图片字段的图片
            调用: download_image(db, module, id_list, field_sign, is_small=True, local_dir="")
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> id_list                 ID列表 (list)
                 --> field_sign              图片字段标识 (str/unicode)
                 --> is_small                是否下载小图 (bool), 默认为True
                 --> local_dir               指定路径 (str/unicode), 默认为temp路径
            返回: 成功返回list
            """             
            global G_tw_http_ip
            global G_tw_token
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
               not isinstance(field_sign, basestring) or not isinstance(is_small, bool) or not isinstance(local_dir, basestring):
                raise Exception("task.download_image argv error, there must be(str/unicode, str/unicode, list,  str/unicode, bool, str/unicode)")             
            return _module.download_image(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.task.__module_type, id_list, field_sign, is_small, local_dir)
        
        @staticmethod
        def set_image(db, module, id_list, field_sign, img_path, compress="1080", exec_event_filter=True):
            u"""
             描述: 更新图片字段的图片
             调用: set_image(db, module, id_list, field_sign, img_path, compress="1080", exec_event_filter=True)
                  --> db                     数据库 (str/unicode)
                  --> module                 模块 (str/unicode)
                  --> id_list                ID列表 (list)
                  --> field_sign             图片字段标识 (str/unicode)
                  --> img_path               图片路径 (str/unicode/list)
                  --> compress               压缩比例 (str/unicode), 可选值 no_compress(无压), 1080(1920x1080), 720(1280x720), 540(960x540)
                  --> exec_event_filter       执行事件过滤器(bool)
             返回: 成功返回True
             """                
            global G_tw_http_ip
            global G_tw_token            
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
                       not isinstance(field_sign, basestring) or not isinstance(img_path, (basestring, list)) or not isinstance(compress, basestring) or not isinstance(exec_event_filter, bool):
                raise Exception("task.set_image argv error, there must be(str/unicode, str/unicode, list, str/unicode, str/unicode/list, str/unicode, bool)")   
            return _module.set_image(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.task.__module_type, id_list, field_sign, img_path, compress, exec_event_filter)

        @staticmethod
        def count(db, module, filter_list):
            u"""
             描述: 统计记录条数
             调用: count(db, module, filter_list)
                  --> db                     数据库 (str/unicode)
                  --> module                 模块 (str/unicode)
                  --> filter_list            过滤语句列表 (list)
             返回: 成功返回str
             """                
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(filter_list, list):
                raise Exception("task.count argv error, there must be(str/unicode, str/unicode, list)")            
            return tw.send_web(tw.task.__name__, "count", {"db":db, "module":module,  "sign_filter_array":filter_list})
        
        @staticmethod
        def distinct(db, module, filter_list, field_sign, order_sign_list=[]):
            u"""
             描述: 获取去重后的记录列表
             调用: distinct(db, module, filter_list, field_sign, order_sign_list=[])
                  --> db                     数据库 (str/unicode)
                  --> module                 模块 (str/unicode)
                  --> filter_list            过滤语句列表 (list)
                  --> field_sign             字段标识 (str/unicode)
                  --> order_sign_list        排序列表 (list)
             返回: 成功返回list
             """               
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(filter_list, list) or \
                       not isinstance(field_sign, basestring) or not isinstance(order_sign_list, list):
                raise Exception("task.distinct argv error, there must be(str/unicode, str/unicode, list, str/unicode, list)")                  
            return tw.send_web(tw.task.__name__, "distinct", {"db":db, "module":module, "distinct_sign":field_sign ,"sign_filter_array":filter_list, "order_sign_array":order_sign_list})

        @staticmethod
        def assign(db, module,  id_list, assign_account_id, start_date="", end_date="" , exec_event_filter=True):
            u"""
             描述: 分配任务给制作人员
             调用: assign(db, module,  id_list, assign_account_id, start_date="", end_date="", exec_event_filter=True)
                  --> db                      数据库 (str/unicode)
                  --> module                  模块 (str/unicode)
                  --> id_list                 ID列表 (list)
                  --> assign_account_id       制作者ID (str/unicode)
                  --> start_date              预计开始日期 (str/unicode), 格式:2018-01-01, 默认为""
                  --> end_date                预计完成日期 (str/unicode), 格式:2018-01-01, 默认为""
                  --> exec_event_filter      执行事件过滤器(bool)
             返回: 成功返回True
             """    
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
                not isinstance(assign_account_id, basestring) or not isinstance(start_date, basestring) \
                    or not isinstance(end_date, basestring) or not isinstance(exec_event_filter, bool):
                raise Exception("task.assign argv error, there must be(str/unicode, str/unicode, list, str/unicode, str/unicode, str/unicode, bool)")   
            return tw.send_web(tw.task.__name__, "assign", {'db':db, 'module':module, 'assign_account_id':assign_account_id, 'start_date':start_date, 'end_date':end_date, 'task_id_array':id_list, 'exec_event_filter':exec_event_filter})
        
        @staticmethod
        def submit(db, module, id, path_list, note="", filebox_sign="review", version="", version_argv={}, note_argv={}, call_back=None, argv_dict={}):
            u"""
             描述: 提交审核,会自动复制文件, 如果文件有上传到网盘, 会自动上传
             调用: submit(db, module, id, path_list, note="", filebox_sign="review", version="", version_argv={}, note_argv={}, call_back=None, argv_dict={})
                  --> db                      数据库 (str/unicode)
                  --> module                  模块 (str/unicode)
                  --> id                      id (str/unicode)
                  --> path_list               文件路径列表 (list); 如拖入bb文件夹和文件test.txt, 则为[z:/aa/bb, z:/aa/test.txt]
                  --> note                    内容 (str/unicode/list),默认为""
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                  --> filebox_sign             提交审核文件标识
                  --> version                 版本号(str/unicode),三位数,如 001, 002     
                  --> version_argv            版本参数(dict)
                  --> note_argv               note参数(dict)
                  --> argv_dict               其他参数(dict). 
                                                目前支持key:is_upload_follow_filebox. 当传入 is_upload_follow_filebox:False时. 不根据文件框设置走(当开启上传网盘功能时. 不会上传网盘)
                                                       key:is_submit. 当传入 is_submit:False时. 不跑流程
             返回: 成功返回True
             """                           
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id, basestring) or \
               not isinstance(path_list, list) or not isinstance(note,(list, basestring)) or not isinstance(filebox_sign, basestring) or not isinstance(version, basestring) or not isinstance(version_argv, dict) \
                   or not isinstance(note_argv, dict) or not isinstance(argv_dict,dict):
                raise Exception("task.submit argv error, there must be(str/unicode, str/unicode, str/unicode, list, str/unicode, str/unicode, str/unicode, dict, dict, dict)")   
            global G_tw_http_ip
            global G_tw_token                
            
            #检查是否提交审核的文件框
            filebox_sign_list=tw.task.get_submit_filebox_sign(db, module, id)
            if not filebox_sign in filebox_sign_list:
                raise Exception("task.submit, The filebox sign ( {} ) not set flow".format(filebox_sign)) #文件框没有设置流程   
            
            note = _dom.to_list(G_tw_http_ip, G_tw_token, db, note)
            return _module.submit(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.task.__module_type, id, filebox_sign, path_list, note, version, version_argv, note_argv, call_back, argv_dict)
        
        @staticmethod
        def update_flow(db, module, id, field_sign, status, note="", image_list=[], retake_pipeline_id_list=[], argv_dict={}):
            u"""
             描述: 修改某审核环节的状态
             调用: update_flow(db, module, id, field_sign, status, note="", image_list=[], retake_pipeline_id_list=[], argv_dict={})
                  --> db                      数据库 (str/unicode)
                  --> module                  模块 (str/unicode)
                  --> id                      id (str/unicode/list)
                  --> field_sign              字段标识 (str/unicode)
                  --> status                  状态 (str/unicode)
                  --> note                    内容 (str/unicode/list) , 默认为""
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                  --> image_list              图片路径列表 (list), 默认为[]
                  --> retake_pipeline_id_list 返修阶段ID列表 (list), 默认为[]
                  --> argv_dict               其他参数(dict)

                  
             返回: 成功返回True
             """               
            global G_tw_http_ip
            global G_tw_token       
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id, (basestring,list)) or \
               not isinstance(field_sign, basestring) or not isinstance(status, basestring) or not isinstance(note, (list,basestring)) or \
               not isinstance(image_list, list) or not isinstance(retake_pipeline_id_list, list) or not isinstance(argv_dict,dict):
                raise Exception("task.update_flow argv error, there must be(str/unicode, str/unicode, str/unicode/list, str/unicode, str/unicode, str/unicode, list, list, dict)")    
            note = _dom.to_list(G_tw_http_ip, G_tw_token, db, note)
            if not isinstance(id,list):
                id = [id]
            return _module.update_flow(tw.send_web, G_tw_http_ip, G_tw_token, db, module, id, field_sign, status, note, image_list, retake_pipeline_id_list, argv_dict)
        
        @staticmethod
        def update_task_status(db, module, id_list, status, note="", image_list=[], retake_pipeline_id_list=[]):
            u"""
             描述: 修改任务状态列
             调用: update_task_status(db, module, id_list, status, note="", image_list=[], retake_pipeline_id_list=[])
                  --> db                      数据库 (str/unicode)
                  --> module                  模块 (str/unicode)
                  --> id_list                 id_list(list)
                  --> status                  状态 (str/unicode)
                  --> note                    内容 (str/unicode/list) , 默认为""
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                  --> image_list              图片路径列表 (list), 默认为[]
                  --> retake_pipeline_id_list 返修阶段ID列表 (list), 默认为[]
             返回: 成功返回True
             """               
            global G_tw_http_ip
            global G_tw_token       
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or \
               not isinstance(status, basestring) or not isinstance(note, (list,basestring)) or \
               not isinstance(image_list, list) or not isinstance(retake_pipeline_id_list, list):
                raise Exception("task.update_task_status argv error, there must be(str/unicode, str/unicode, list, str/unicode, str/unicode, list, list)")    
            note = _dom.to_list(G_tw_http_ip, G_tw_token, db, note)
            return _module.update_task_status(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.task.__module_type, id_list, status, note, image_list, retake_pipeline_id_list)


        @staticmethod
        def group_count(db, module, field_sign_list, filter_list):
            u"""
             描述: 按字段标识进行分组统计条数
             调用: group_count(db, module, field_sign_list, filter_list)
                  --> db                    数据库 (str/unicode)
                  --> module                模块 (str/unicode)
                  --> field_sign_list       字段标识列表 (list)
                  --> filter_list           过滤语句列表 (list)
             返回: 成功返回list
             """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(field_sign_list, list) or \
                       not isinstance(filter_list, list) :
                raise Exception("task.group_count argv error, there must be(str/unicode, str/unicode, list, list)")              
            return tw.send_web(tw.task.__name__, "group_count", {"db":db, "module":module, "sign_array":field_sign_list, "sign_filter_array":filter_list})
        
        @staticmethod
        def send_msg(db, module, id, account_id_list, content="", important=False, argv_dict={}):
            u"""
             描述: 给指定用户发送任务相关消息
             调用: send_msg(db, module, id, account_id_list, content="", important=False, argv_dict={})
                   --> db                      数据库 (str/unicode)
                   --> module                  模块 (str/unicode)
                   --> id                      信息ID (str/unicode)
                   --> account_id_list         账号ID列表 (list)
                   --> content                 发送的内容 (str/unicode/list) 
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                   --> important                是否强提醒
                   --> argv_dict                其他参数(dict)，目前支持key:ignore_path. 当传入 ignore_path:True,则消息不会有路径
             返回: 成功返回True
             """   
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or  not isinstance(id, basestring) or not isinstance(account_id_list, list) or \
                not isinstance(content, (list,basestring)) or not isinstance(important, bool) or not isinstance(argv_dict,dict):
                raise Exception("task.send_msg argv error ,there must be (str/unicode, str/unicode, str/unicode, str/unicode, list,  str/unicode, bool, dict)")
            content = _dom.to_list(G_tw_http_ip, G_tw_token, db, content)
            t_dic={"db":db, "module":module, "task_id":id, "account_id_array":account_id_list, "content":content, "important":important}
            t_dic  = dict(list(argv_dict.items()) +list(t_dic.items()))
            return tw.send_web(tw.task.__name__, "send_msg", t_dic)
        
        @staticmethod
        def set_media(db, module, id_list, field_sign, data_list, exec_event_filter=True):
            """
            描述:更新多媒体字段
            调用:set_media(db, module, id_list, field_sign, data_list, exec_event_filter=True)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign             字段标识 (str/unicode)
                 --> data_list              文件列表['1.jpg','z:/1.mov','1.txt']
                 --> exec_event_filter       执行事件过滤器(bool)
            返回:成功返回True
            """
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or\
               not isinstance(field_sign, basestring) or not isinstance(data_list, list) or not isinstance(exec_event_filter, bool): 
                raise Exception("task.set_media argv error, there must be (str/unicode, str/unicode, list, str/unicode, list, bool)")
       
            return _module.set_media(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.task.__module_type, id_list, field_sign, data_list, exec_event_filter)
        
        @staticmethod
        def append_media(db, module, id_list, field_sign, data_list, a_append_after=True, exec_event_filter=True):
            """
            描述:追加多媒体字段
            调用:append_media(db, module, id_list, field_sign, data_list, a_append_after=True, exec_event_filter=True)
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign             字段标识 (str/unicode)
                 --> data_list              文件列表['1.jpg','z:/1.mov','1.txt']  
                 --> append_after           默认往后追加
                 --> exec_event_filter      执行事件过滤器(bool)
            返回:成功返回True                        
            """
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or\
               not isinstance(field_sign, basestring) or not isinstance(data_list, list) or not isinstance(a_append_after, bool) or not isinstance(exec_event_filter, bool):
                raise Exception("task.append_media argv error, there must be (str/unicode, str/unicode, list, str/unicode, list, bool, bool)")
                             
            return _module.append_media(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.task.__module_type, id_list, field_sign, data_list, a_append_after, exec_event_filter)
        
        @staticmethod
        def download_media(db, module, id_list, field_sign, local_dir=''):
            """
            描述:下载多媒体字段
            调用:download_media(db, module, id_list, field_sign, local_dir="")
                 --> db                     数据库 (str/unicode)
                 --> module                 模块 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign             字段标识 (str/unicode)
                 --> local_dir              保存目录,默认为temp路径     
            返回:列表. 
            """
            
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id_list, list) or\
               not isinstance(field_sign, basestring) or not isinstance(local_dir, basestring):
                raise Exception("task.download_media argv error, there must be (str/unicode, str/unicode, list, str/unicode, str/unicode)")
            
            return _module.download_media(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.task.__module_type, id_list, field_sign, local_dir)
        
        @staticmethod
        def publish(db, module, id, path_list, filebox_sign, version="", version_argv={}, note="", note_argv={}, call_back=None, argv_dict={}):
            """
            描述:发布版本
            调用:publish(db, module, id, path_list, filebox_sign, version="", version_argv={}, note="", note_argv={}, call_back=None, argv_dict={})
                 ---> db                     数据库 (str/unicode)
                 ---> module                 模块 (str/unicode)
                 ---> id                     ID (str/unicode)
                 ---> path_list              本地文件列表(list)
                 ---> filebox_sign           文件框标识 (str/unicode)
                 ---> version                版本号(str/unicode),三位数,如 001, 002     
                 ---> version_argv           版本参数(dict)
                 ---> note                   内容 (str/unicode/list),默认为""
                                             list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                             [{"type":"text","content":"te"},
                                             {"type":"a","title":"aa","url":"g:/1.jpg"},
                                             {"type":"image","path":"1.jpg"},
                                             {"type":"attachment","path":"1.txt"}]
                ---> note_argv               note参数(dict)
                ---> argv_dict               其他参数(dict). 
                                                目前支持key:is_upload_follow_filebox. 当传入 is_upload_follow_filebox:False时. 不根据文件框设置走(当开启上传网盘功能时. 不会上传网盘)
                                                       key:is_submit. 当传入 is_submit:False时. 不跑流程

            返回: 成功返回True
            """
                     
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(id, basestring) or not isinstance(path_list, list) or\
               not isinstance(filebox_sign, basestring) or not isinstance(version, basestring) or not isinstance(version_argv, dict) or not isinstance(note,(list, basestring)) \
                   or not isinstance(note_argv, dict) or not isinstance(argv_dict,dict):
                raise Exception("task.publish argv error, there must be (str/unicode, str/unicode, str/unicode, list, str/unicode, str/unicode, str/unicode, dict, str/unicode/list, dict, dict)")
            
            global G_tw_http_ip
            global G_tw_token                
            note = _dom.to_list(G_tw_http_ip, G_tw_token, db, note)            
            return _module.publish(tw.send_web, G_tw_http_ip, G_tw_token, db, module, tw.task.__module_type, id, path_list, filebox_sign, version, version_argv, note, note_argv, call_back, argv_dict)
  
    class etask:
        
        @staticmethod
        def fields(db):
            u"""
            描述: 获取所有字段标识
            调用: fields(db)
                  --> db                    数据库 (str/unicode)
            返回: 成功返回list
            """              
            if not isinstance(db, basestring):
                raise Exception("etask.fields argv error, there must be(str/unicode)")    
            return tw.send_web(tw.etask.__name__, "fields", {"db":db})
        
        @staticmethod
        def fields_and_str(db):
            u"""
            描述: 获取所有字段标识
            调用: fields_and_str(db)
                  --> db                    数据库 (str/unicode)
            返回: 成功返回list
            """              
            if not isinstance(db, basestring):
                raise Exception("etask.fields argv error, there must be(str/unicode)")                  
            return tw.send_web(tw.etask.__name__, "fields_and_str", {"db":db})  
               
            
        @staticmethod
        def get_id(db, filter_list, limit="5000", start_num=""):
            u"""
            描述: 获取记录id列表
            调用: get_id(db, filter_list, limit="5000", start_num="")
                 --> db                     数据库 (str/unicode)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> start_num              起始条数 (str/unicode), 默认为""
            返回: 成功返回list
            """                  
            if not isinstance(db, basestring) or not isinstance(filter_list, list) or \
                       not isinstance(limit, basestring) or not isinstance(start_num, basestring):
                raise Exception("etask.get_id argv error, there must be(str/unicode, str/unicode, list, str/unicode, str/unicode)")                 
            return tw.send_web(tw.etask.__name__, "get_id", {"db":db, "sign_filter_array":filter_list, "limit":limit, "start_num":start_num})
                    
        @staticmethod
        def get(db, id_list, field_sign_list, limit="5000", order_sign_list=[]):
            u"""
            描述: 获取记录列表
            调用: get(db, id_list, field_sign_list, limit="5000", order_sign_list=[])
                 --> db                     数据库 (str/unicode)
                 --> id_list                ID列表 (list)(最大长度20000)
                 --> field_sign_list        字段标识列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_sign_list        排序的字段标识列表 (list)
            返回: 成功返回list
            """                 
            if not isinstance(db, basestring) or not isinstance(id_list, list) or \
                       not isinstance(field_sign_list, list)  or not isinstance(limit, basestring) or not isinstance(order_sign_list, list):
                raise Exception("etask.get argv error, there must be(str/unicode, str/unicode, list, list, str/unicode, list)")  
            
            return _module_e.get(tw.send_web, db, id_list, field_sign_list, limit, order_sign_list)       
        
        @staticmethod
        def get_filter(db, field_sign_list, filter_list, limit="5000", order_sign_list=[], start_num=""):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, field_sign_list, filter_list, limit="5000", order_sign_list=[], start_num="")
                 --> db                     数据库 (str/unicode)
                 --> field_sign_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_sign_list        顺序的字段标识列表 (list)
                 --> start_num               开始条数 (str/unicode), 默认为""
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(field_sign_list, list) or not isinstance(filter_list, list)  or not isinstance(limit, basestring) or not isinstance(order_sign_list, list) or not isinstance(start_num, basestring):
                raise Exception("etask.get_filter argv error, there must be(tr/unicode, list, list, str/unicode, list, str)")   
            
            return tw.send_web(tw.etask.__name__, "get_filter", {"db":db, "sign_array":field_sign_list, "sign_filter_array":filter_list, "order_sign_array":order_sign_list, "limit":limit, "start_num":start_num})
                
        
        @staticmethod
        def get_dir(db, id_list, folder_sign_list):
            u"""
            描述: 用目录标识列表获取对应的目录列表
            调用: get_dir(db, id_list, folder_sign_list)
                 --> db                      数据库 (str/unicode)
                 --> id_list                 ID列表 (list)
                 --> folder_sign_list        目录标识列表 (list)

            返回: 成功返回list
            """            
            if not isinstance(db, basestring) or not isinstance(id_list, list) or \
                       not isinstance(folder_sign_list, list) :
                raise Exception("etask.get_dir argv error, there must be(str/unicode, list, list)")               
            return tw.send_web(tw.etask.__name__, "get_dir", {"db":db, "sign_array":folder_sign_list, "id_array":id_list, "os":_lib.get_os()}) 
        
        @staticmethod
        def get_field_and_dir(db, id_list, field_sign_list, folder_sign_list):
            u"""
            描述: 用目录标识列表和字段标识列表获取对应的目录和字段列表
            调用: get_field_and_dir(db, id_list, field_sign_list, folder_sign_list)
                 --> db                      数据库 (str/unicode)
                 --> id_list                 ID列表 (list)
                 --> field_sign_list         字段标识列表 (list)
                 --> folder_sign_list        目录标识列表 (list)

            返回: 成功返回list
            """      
            if not isinstance(db, basestring) or not isinstance(id_list, list) or \
                       not isinstance(field_sign_list, list) or not isinstance(folder_sign_list, list):
                raise Exception("etask.get_field_and_dir argv error, there must be(str/unicode, str/unicode, list, list, list)")               
            return tw.send_web(tw.etask.__name__, "get_field_and_dir", {"db":db, "field_sign_array":field_sign_list, "folder_sign_array":folder_sign_list,"id_array":id_list, "os":_lib.get_os()})      
                
        @staticmethod
        def get_makedirs(db, id_list):
            u"""
            描述:获取创建目录的列表
            调用:get_makedirs(db, id_list)
                 --> db                      数据库 (str/unicode)
                 --> id_list                 ID列表 (list)
            返回: 成功返回list
             """             
            if not isinstance(db, basestring) or not isinstance(id_list, list):
                raise Exception("etask.get_makedirs argv error, there must be(str/unicode, list)")                
            return _module_e.get_makedirs(tw.send_web, db, id_list)
        
        @staticmethod
        def get_submit_filebox_sign(db, id):
            u"""
            描述: 获取提交流程的文件框标识列表
            调用: get_submit_filebox_sign(db, id)
                 --> db                      数据库 (str/unicode)
                 --> id                      ID (str/unicode)
            返回: 成功返回list
            """                
            if not isinstance(db, basestring) or not isinstance(id, basestring):
                raise Exception("etask.get_submit_filebox argv error, there must be(str/unicode, str/unicode)")             
            return tw.send_web(tw.etask.__name__, "get_submit_filebox_sign", {"db":db, "id":id}) 
                    
        @staticmethod
        def get_sign_filebox(db, id, filebox_sign):
            u"""
            描述: 根据文件框标识获取文件框设置信息
            调用: get_sign_filebox(db, id, filebox_sign)
                 --> db                      数据库 (str/unicode)
                 --> id                      ID (str/unicode)
                 --> filebox_sign            文件框标识 (str/unicode)
            返回: 成功返回dict
            """                  
            if not isinstance(db, basestring) or not isinstance(id, basestring) or \
                       not isinstance(filebox_sign, basestring):
                raise Exception("etask.get_sign_filebox argv error, there must be(str/unicode, str/unicode, str/unicode)")              
            return tw.send_web(tw.etask.__name__, "get_sign_filebox", {"db":db, "id":id, "os":_lib.get_os(), "filebox_sign":filebox_sign})
        
        @staticmethod
        def get_filebox(db, id, filebox_id):
            u"""
            描述: 获取文件框设置信息
            调用: get_filebox(db, id, filebox_id)
                 --> db                      数据库 (str/unicode)
                 --> id                      ID (str/unicode)
                 --> filebox_id              文件框ID (str/unicode)
            返回: 成功返回dict
            """                
            if not isinstance(db, basestring) or not isinstance(id, basestring) or \
                       not isinstance(filebox_id, basestring):
                raise Exception("etask.get_filebox argv error, there must be(str/unicode, str/unicode, str/unicode)")              
            return tw.send_web(tw.etask.__name__, "get_filebox", {"db":db, "id":id, "os":_lib.get_os(), "filebox_id":filebox_id})
        
        @staticmethod
        def get_review_file(db, id_list):
            u"""
            描述: 获取可预览最后版本文件,用于视频串播
            调用: get_review_file(db, id_list)
                 --> db                      数据库 (str/unicode)
                 --> id_list                 ID (list)
            返回: 成功返回list
            """     
            if not isinstance(db, basestring) or not isinstance(id_list, list):
                raise Exception("etask.get_review_file argv error, there must be(str/unicode, list)")  
            
            return tw.send_web(tw.etask.__name__, "get_review_file", {"db":db, "link_id_array":id_list, "os":_lib.get_os()}) 
                
        @staticmethod
        def get_version_file(db, id_list, filebox_sign):
            u"""
            描述: 获取文件框最后版本文件
            调用: get_version_file(db, id_list, filebox_sign)
                 --> db                      数据库 (str/unicode)
                 --> id_list                 ID (list)
                 --> filebox_sign            文件框标识(str/unicode)
            返回: 成功返回list
            """     
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not isinstance(filebox_sign, basestring) :
                raise Exception("etask.get_version_file argv error, there must be(str/unicode, list, str/unicode)")              
            return tw.send_web(tw.etask.__name__, "get_version_file", {"db":db, "link_id_array":id_list, "filebox_sign":filebox_sign, "os":_lib.get_os()}) 
     
        
        @staticmethod
        def set(db, id_list, sign_data_dict, exec_event_filter=True):
            u"""
            描述: 更新记录
            调用: set(db, id_list, sign_data_dict, exec_event_filter=True)
                 --> db                      数据库 (str/unicode)
                 --> id_list                 ID (list)
                 --> sign_data_dict          更新数据 (dict), 格式:{"字段标识" : "值", "字段标识" : "值" }
                 --> exec_event_filter       执行事件过滤器(bool)
            返回: 成功返回True
            """     
            if not isinstance(db, basestring) or not isinstance(id_list, list) or \
                       not isinstance(sign_data_dict, dict ) or not isinstance(exec_event_filter, bool):
                raise Exception("etask.set argv error, there must be(str/unicode, list, dict, bool)")              
            return _module_e.set(tw.send_web, db, id_list, sign_data_dict, exec_event_filter)

        @staticmethod
        def delete(db, id_list, exec_event_filter=True):
            u"""
            描述: 删除记录
            调用: delete(db, id_list, exec_event_filter=True)
                 --> db                      数据库 (str/unicode)
                 --> id_list                 ID列表 (list)
                 --> exec_event_filter       执行事件过滤器(bool)
            返回: 成功返回True
            """             
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not isinstance(exec_event_filter, bool):
                raise Exception("etask.delete argv error, there must be(str/unicode, list, bool)")        
            return tw.send_web(tw.etask.__name__, "delete", {"db":db, "id_array":id_list,"exec_event_filter":exec_event_filter})
        
        @staticmethod
        def create(db, type_sign, sign_data_dict, exec_event_filter=True):
            u"""
            描述: 创建记录
            调用: create(db, type_sign, sign_data_dict)
                 --> db                     数据库 (str/unicode)
                 --> type_sign              任务类型标识 (str/unicode)
                 --> sign_data_dict         创建的数据 (dict), 格式:{字段标识1: 值1, 字段标识2: 值2, 字段标识3:值3}
                                            目前支持自定义任务ID. 例如:{'etask.id':'1234abcd'}
                --> exec_event_filter       执行事件过滤器(bool)
            返回: 成功返回id
            """          
            if not isinstance(db, basestring) or not isinstance(type_sign, basestring) or not isinstance(sign_data_dict, dict) or not isinstance(exec_event_filter, bool):
                raise Exception("etask.create argv error, there must be(str/unicode, str/unicode, dict, bool)") 
            return tw.send_web(tw.etask.__name__, "create", {"db":db, "type_sign":type_sign, "sign_data_array":sign_data_dict,  "exec_event_filter":exec_event_filter})  
        
        @staticmethod
        def create_task(db, join_id, pipeline_id, task_name, flow_id, sub_pipeline_id="", pipeline_template_id="",sign_data_dict={}, exec_event_filter=True):
            u"""
            描述: 创建记录
            调用: create_task(db, join_id, pipeline_id, task_name, flow_id, sub_pipeline_id="", pipeline_template_id="",sign_data_dict={}, exec_event_filter=True)
                 --> db                      数据库 (str/unicode)
                 --> join_id                 信息表的ID (str/unicode)
                 --> pipeline_id             阶段ID (str/unicode)
                 --> task_name               任务名称 (str/unicode)
                 --> flow_id                 流程ID (str/unicode)
                 --> sub_pipeline_id         子阶段ID (str/unicode)
                 --> pipeline_template_id    阶段流程ID (str/unicode)
                 --> sign_data_dict         创建的数据 (dict), 格式:{字段标识1: 值1, 字段标识2: 值2, 字段标识3:值3}
                                            目前支持自定义任务ID. 例如:{'etask.id':'1234abcd'}
                 --> exec_event_filter       执行事件过滤器(bool)
            返回: 成功返回ID
            """            
            if not isinstance(db, basestring) or not isinstance(join_id, basestring) or \
               not isinstance(pipeline_id, basestring) or not isinstance(task_name, basestring) or not isinstance(flow_id, basestring) or not isinstance(sub_pipeline_id, basestring) or not isinstance(pipeline_template_id, basestring) \
                   or not isinstance(sign_data_dict,dict) or not isinstance(exec_event_filter, bool):
                raise Exception("etask.create_task argv error, there must be(str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, dict, bool)")    
            return tw.send_web(tw.etask.__name__, "create_task", {"db":db, "join_id":join_id, "pipeline_id":pipeline_id, "sub_pipeline_id":sub_pipeline_id, "flow_id":flow_id, "task_name":task_name, "pipeline_template_id":pipeline_template_id,'sign_data_array':sign_data_dict, 'exec_event_filter':exec_event_filter})

        @staticmethod
        def download_image(db, id_list, field_sign, is_small=True, local_dir=""):
            u"""
            描述: 下载图片字段的图片
            调用: download_image(db, id_list, field_sign, is_small=True, local_dir="")
                 --> db                      数据库 (str/unicode)
                 --> id_list                 ID列表 (list)
                 --> field_sign              图片字段标识 (str/unicode)
                 --> is_small                是否下载小图 (bool), 默认为True
                 --> local_dir               指定路径 (str/unicode), 默认为temp路径
            返回: 成功返回list
            """             
            global G_tw_http_ip
            global G_tw_token
            if not isinstance(db, basestring) or not isinstance(id_list, list) or \
               not isinstance(field_sign, basestring) or not isinstance(is_small, bool) or not isinstance(local_dir, basestring):
                raise Exception("etask.download_image argv error, there must be(str/unicode, list,  str/unicode, bool, str/unicode)")             
            return _module_e.download_image(tw.send_web, G_tw_http_ip, G_tw_token, db, id_list, field_sign, is_small, local_dir)
        
        @staticmethod
        def set_image(db, id_list, field_sign, img_path, compress="1080", exec_event_filter=True):
            u"""
             描述: 更新图片字段的图片
             调用: set_image(db, id_list, field_sign, img_path, compress="1080", exec_event_filter=True)
                  --> db                     数据库 (str/unicode)
                  --> id_list                ID列表 (list)
                  --> field_sign             图片字段标识 (str/unicode)
                  --> img_path               图片路径 (str/unicode/list)
                  --> compress               压缩比例 (str/unicode), 可选值 no_compress(无压), 1080(1920x1080), 720(1280x720), 540(960x540)
                  --> exec_event_filter       执行事件过滤器(bool)
             返回: 成功返回True
             """                
            global G_tw_http_ip
            global G_tw_token            
            if not isinstance(db, basestring) or not isinstance(id_list, list) or \
                       not isinstance(field_sign, basestring) or not isinstance(img_path, (basestring, list)) or not isinstance(compress, basestring) or not isinstance(exec_event_filter, bool):
                raise Exception("etask.set_image argv error, there must be(str/unicode, list, str/unicode, str/unicode/list, str/unicode, bool)")   
            return _module_e.set_image(tw.send_web, G_tw_http_ip, G_tw_token, db, id_list, field_sign, img_path, compress, exec_event_filter)

        @staticmethod
        def count(db, filter_list):
            u"""
             描述: 统计记录条数
             调用: count(db, filter_list)
                  --> db                     数据库 (str/unicode)
                  --> filter_list            过滤语句列表 (list)
             返回: 成功返回str
             """                
            if not isinstance(db, basestring) or not isinstance(filter_list, list):
                raise Exception("etask.count argv error, there must be(str/unicode, list)")            
            return tw.send_web(tw.etask.__name__, "count", {"db":db, "sign_filter_array":filter_list})
        
        @staticmethod
        def distinct(db, filter_list, field_sign, order_sign_list=[]):
            u"""
             描述: 获取去重后的记录列表
             调用: distinct(db, filter_list, field_sign, order_sign_list=[])
                  --> db                     数据库 (str/unicode)
                  --> filter_list            过滤语句列表 (list)
                  --> field_sign             字段标识 (str/unicode)
                  --> order_sign_list        排序列表 (list)
             返回: 成功返回list
             """               
            if not isinstance(db, basestring) or not isinstance(filter_list, list) or \
                       not isinstance(field_sign, basestring) or not isinstance(order_sign_list, list):
                raise Exception("etask.distinct argv error, there must be(str/unicode, list, str/unicode, list)")                  
            return tw.send_web(tw.etask.__name__, "distinct", {"db":db, "distinct_sign":field_sign ,"sign_filter_array":filter_list, "order_sign_array":order_sign_list})

        
        @staticmethod
        def assign(db, id_list, assign_account_id, start_date="", end_date="", exec_event_filter=True):
            u"""
             描述: 分配任务给制作人员
             调用: assign(db,  id_list, assign_account_id, start_date="", end_date="", exec_event_filter=True)
                  --> db                      数据库 (str/unicode)
                  --> id_list                 ID列表 (list)
                  --> assign_account_id       制作者ID (str/unicode)
                  --> start_date              预计开始日期 (str/unicode), 格式:2018-01-01, 默认为""
                  --> end_date                预计完成日期 (str/unicode), 格式:2018-01-01, 默认为""
                  --> exec_event_filter      执行事件过滤器(bool)
             返回: 成功返回True
             """    
            if not isinstance(db, basestring) or not isinstance(id_list, list) or \
                       not isinstance(assign_account_id, basestring) or not isinstance(start_date, basestring) or not isinstance(end_date, basestring) or not isinstance(exec_event_filter, bool):
                raise Exception("etask.assign argv error, there must be(str/unicode, list, str/unicode, str/unicode, str/unicode, bool)")   
            return tw.send_web(tw.etask.__name__, "assign", {'db':db, 'assign_account_id':assign_account_id, 'start_date':start_date, 'end_date':end_date, 'task_id_array':id_list, 'exec_event_filter':exec_event_filter})
        
        @staticmethod
        def submit(db, id, path_list, note="", filebox_sign="review", version="", version_argv={}, note_argv={}, call_back=None, argv_dict={}):
            u"""
             描述: 提交审核,会自动复制文件, 如果文件有上传到网盘, 会自动上传
             调用: submit(db, id, path_list, note="", filebox_sign="review", version="", version_argv={}, note_argv={}, call_back=None, argv_dict={})
                  --> db                      数据库 (str/unicode)
                  --> id                      id (str/unicode)
                  --> path_list               文件路径列表 (list); 如拖入bb文件夹和文件test.txt, 则为[z:/aa/bb, z:/aa/test.txt]
                  --> note                    内容 (str/unicode/list),默认为""
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                  --> filebox_sign             提交审核文件标识
                  --> version                 版本号(str/unicode),三位数,如 001, 002     
                  --> version_argv            版本参数(dict)
                  --> note_argv               note参数(dict)
                  --> argv_dict               其他参数(dict). 
                                                目前支持key:is_upload_follow_filebox. 当传入 is_upload_follow_filebox:False时. 不根据文件框设置走(当开启上传网盘功能时. 不会上传网盘)

             返回: 成功返回True
             """                           
            if not isinstance(db, basestring) or not isinstance(id, basestring) or \
               not isinstance(path_list, list) or not isinstance(note,(list, basestring)) or not isinstance(filebox_sign, basestring) or not isinstance(version, basestring) or not isinstance(version_argv, dict) \
                   or not isinstance(note_argv, dict) or not isinstance(argv_dict,dict):
                raise Exception("etask.submit argv error, there must be(str/unicode, str/unicode, list, str/unicode, str/unicode, str/unicode, dict, dict, dict)")   
            global G_tw_http_ip
            global G_tw_token                
            
            #检查是否提交审核的文件框
            filebox_sign_list=tw.etask.get_submit_filebox_sign(db, id)
            if not filebox_sign in filebox_sign_list:
                raise Exception("etask.submit, The filebox sign ( {} ) not set flow".format(filebox_sign)) #文件框没有设置流程   
            
            note = _dom.to_list(G_tw_http_ip, G_tw_token, db, note)
            return _module_e.submit(tw.send_web, G_tw_http_ip, G_tw_token, db, id, filebox_sign, path_list, note, version, version_argv, note_argv, call_back, argv_dict)
        
        @staticmethod
        def update_flow(db, id, field_sign, status, note="", image_list=[], retake_pipeline_id_list=[], argv_dict={}):
            u"""
             描述: 修改某审核环节的状态
             调用: update_flow(db, id, field_sign, status, note="", image_list=[], retake_pipeline_id_list=[], argv_dict={})
                  --> db                      数据库 (str/unicode)
                  --> id                      id (str/unicode/list)
                  --> field_sign              字段标识 (str/unicode)
                  --> status                  状态 (str/unicode)
                  --> note                    内容 (str/unicode/list) , 默认为""
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                  --> image_list              图片路径列表 (list), 默认为[]
                  --> retake_pipeline_id_list 返修阶段ID列表 (list), 默认为[]
                  --> argv_dict               其他参数(dict)
             返回: 成功返回True
             """               
            global G_tw_http_ip
            global G_tw_token       
            if not isinstance(db, basestring) or not isinstance(id, (basestring,list)) or \
               not isinstance(field_sign, basestring) or not isinstance(status, basestring) or not isinstance(note, (list,basestring)) or \
               not isinstance(image_list, list) or  not isinstance(retake_pipeline_id_list, list) or not isinstance(argv_dict,dict):
                raise Exception("etask.update_flow argv error, there must be(str/unicode, str/unicode/list, str/unicode, str/unicode, str/unicode, list, dict)")    
            note = _dom.to_list(G_tw_http_ip, G_tw_token, db, note)
            if not isinstance(id,list):
                id = [id]
            return _module_e.update_flow(tw.send_web, G_tw_http_ip, G_tw_token, db, id, field_sign, status, note, image_list, retake_pipeline_id_list, argv_dict)
        

        @staticmethod
        def update_task_status(db, id_list, status, note="", image_list=[], retake_pipeline_id_list=[]):
            u"""
             描述: 修改任务状态列
             调用: update_task_status(db, module, id_list, status, note="", image_list=[], retake_pipeline_id_list=[])
                  --> db                      数据库 (str/unicode)
                  --> id_list                 id_list(list)
                  --> status                  状态 (str/unicode)
                  --> note                    内容 (str/unicode/list) , 默认为""
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                  --> image_list              图片路径列表 (list), 默认为[]
                  --> retake_pipeline_id_list 返修阶段ID列表 (list), 默认为[]
             返回: 成功返回True
             """               
            global G_tw_http_ip
            global G_tw_token       
            if not isinstance(db, basestring)  or not isinstance(id_list, list) or \
               not isinstance(status, basestring) or not isinstance(note, (list,basestring)) or \
               not isinstance(image_list, list) or not isinstance(retake_pipeline_id_list, list):
                raise Exception("etask.update_task_status argv error, there must be(str/unicode, list, str/unicode, str/unicode, list, list)")    
            note = _dom.to_list(G_tw_http_ip, G_tw_token, db, note)
            return _module_e.update_task_status(tw.send_web, G_tw_http_ip, G_tw_token, db, id_list, status, note, image_list, retake_pipeline_id_list)


        @staticmethod
        def group_count(db, field_sign_list, filter_list):
            u"""
             描述: 按字段标识进行分组统计条数
             调用: group_count(db, field_sign_list, filter_list)
                  --> db                    数据库 (str/unicode)
                  --> field_sign_list       字段标识列表 (list)
                  --> filter_list           过滤语句列表 (list)
             返回: 成功返回list
             """             
            if not isinstance(db, basestring) or not isinstance(field_sign_list, list) or \
                       not isinstance(filter_list, list) :
                raise Exception("etask.group_count argv error, there must be(str/unicode, list, list)")              
            return tw.send_web(tw.etask.__name__, "group_count", {"db":db, "sign_array":field_sign_list, "sign_filter_array":filter_list})
        
        @staticmethod
        def send_msg(db, id, account_id_list, content="", important=False):
            u"""
             描述: 给指定用户发送任务相关消息
             调用: send_msg(db, id, account_id_list, content="", important=False)
                   --> db                      数据库 (str/unicode)
                   --> id                      信息ID (str/unicode)
                   --> account_id_list         账号ID列表 (list)
                   --> content                 发送的内容 (str/unicode/list) 
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                   --> important                是否强提醒
             返回: 成功返回True
             """   
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or  not isinstance(id, basestring) or not isinstance(account_id_list, list) or \
                not isinstance(content, (list,basestring)) or not isinstance(important, bool):
                raise Exception("etask.send_msg argv error ,there must be (str/unicode, str/unicode, list,  str/unicode, bool)")
            content = _dom.to_list(G_tw_http_ip, G_tw_token, db, content)
            return tw.send_web(tw.etask.__name__, "send_msg", {"db":db, "task_id":id, "account_id_array":account_id_list, "content":content, "important":important})
        
        @staticmethod
        def set_media(db, id_list, field_sign, data_list, exec_event_filter=True):
            """
            描述:更新多媒体字段
            调用:set_media(db, id_list, field_sign, data_list, exec_event_filter=True)
                 --> db                     数据库 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign             字段标识 (str/unicode)
                 --> data_list              文件列表['1.jpg','z:/1.mov','1.txt']
                 --> exec_event_filter       执行事件过滤器(bool)
            返回:成功返回True
            """
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(id_list, list) or\
               not isinstance(field_sign, basestring) or not isinstance(data_list, list):
                raise Exception("etask.set_media argv error, there must be (str/unicode, list, str/unicode, list, bool)")
       
            return _module_e.set_media(tw.send_web, G_tw_http_ip, G_tw_token, db, id_list, field_sign, data_list, exec_event_filter)
        
        @staticmethod
        def append_media(db, id_list, field_sign, data_list, a_append_after=True, exec_event_filter=True):
            """
            描述:追加多媒体字段
            调用:append_media(db, id_list, field_sign, data_list, a_append_after=True, exec_event_filter=True)
                  --> db                     数据库 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign             字段标识 (str/unicode)
                 --> data_list              文件列表['1.jpg','z:/1.mov','1.txt']
                 --> append_after           默认往后追加
                 --> exec_event_filter      执行事件过滤器(bool)
            返回:成功返回True                        
            """
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not isinstance(field_sign, basestring) or \
               not isinstance(data_list, list) or not isinstance(a_append_after, bool) or not isinstance(exec_event_filter, bool):
                raise Exception("etask.append_media argv error, there must be (str/unicode, list, str/unicode, list, bool, bool)")
                             
            return _module_e.append_media(tw.send_web, G_tw_http_ip, G_tw_token, db, id_list, field_sign, data_list, a_append_after, exec_event_filter)
            
        @staticmethod
        def download_media(db, id_list, field_sign, local_dir=''):
            """
            描述:下载多媒体字段
            调用:download_media(db, id_list, field_sign, local_dir="")
                 --> db                     数据库 (str/unicode)
                 --> id_list                ID列表 (list)
                 --> field_sign             字段标识 (str/unicode)
                 --> local_dir              保存目录,默认为temp路径     
            返回:列表. 
            """
            
            global G_tw_http_ip
            global G_tw_token              
            if not isinstance(db, basestring) or not isinstance(id_list, list) or\
               not isinstance(field_sign, basestring) or not isinstance(local_dir, basestring):
                raise Exception("etask.download_media argv error, there must be (str/unicode, list, str/unicode, str/unicode)")
            
            return _module_e.download_media(tw.send_web, G_tw_http_ip, G_tw_token, db, id_list, field_sign, local_dir)
        
        @staticmethod
        def publish(db, id, path_list, filebox_sign, version="", version_argv={}, note="", note_argv={}, call_back=None, argv_dict={}):
            """
            描述:发布版本
            调用:publish(db, id, path_list, filebox_sign, version="", version_argv={}, note="", note_argv={}, call_back=None, argv_dict={})
                 --> db                     数据库 (str/unicode)
                 --> id                     ID (str/unicode)
                 --> path_list              本地文件列表(list)
                 --> filebox_sign           文件框标识 (str/unicode)
                 --> version                版本号(str/unicode),三位数,如 001, 002    
                 --> version_argv            版本参数(dict)
                ---> note                   内容 (str/unicode/list),默认为""
                                            list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                            [{"type":"text","content":"te"},
                                             {"type":"a","title":"aa","url":"g:/1.jpg"},
                                             {"type":"image","path":"1.jpg"},
                                             {"type":"attachment","path":"1.txt"}]
                ---> note_argv               note参数(dict)
                --> argv_dict               其他参数(dict). 
                                                目前支持key:is_upload_follow_filebox. 当传入 is_upload_follow_filebox:False时. 不根据文件框设置走(当开启上传网盘功能时. 不会上传网盘)

            返回: 成功返回True
            """
            
        
            if not isinstance(db, basestring) or not isinstance(id, basestring) or not isinstance(path_list, list) or\
               not isinstance(filebox_sign, basestring) or not isinstance(version, basestring) or not isinstance(version_argv, dict) or not isinstance(note,(list, basestring)) \
                   or not isinstance(note_argv, dict) or not isinstance(argv_dict,dict):
                raise Exception("etask.publish argv error, there must be (str/unicode, str/unicode, str/unicode, list, str/unicode, str/unicode, str/unicode, dict, str/unicode/list, dict, dict)")
            global G_tw_http_ip
            global G_tw_token          
            note = _dom.to_list(G_tw_http_ip, G_tw_token, db, note)
            return _module_e.publish(tw.send_web, G_tw_http_ip, G_tw_token, db, id, path_list, filebox_sign, version, version_argv, note, note_argv, call_back, argv_dict)
   
    class etask_type:
        u'''简易版项目的任务类型'''
        
        @staticmethod
        def fields():
            u"""
             描述:获取所有字段标识
             调用:fields()
             返回:成功返回list
             """   
            return tw.send_web(tw.etask_type.__name__, "fields", {})

        
        @staticmethod
        def get_id(db, filter_list):
            u"""
             描述:获取记录id列表
             调用:get_id(db, filter_list)
                  --> db                    数据库 (str/unicode)
                  --> filter_list           过滤语句列表 (list)
             返回:成功返回list
             """              
            if not isinstance(db, basestring) or not isinstance(filter_list, list):
                raise Exception("etask_type.get_id argv error ,there must be (str/unicode, list)")          
            return tw.send_web(tw.etask_type.__name__, "get_id", {"db":db, "filter_array":filter_list})
                    
        @staticmethod
        def get(db, id_list, field_list):
            u"""
             描述:获取记录列表
             调用:get(db, id_list, field_list)
                  --> db                   数据库 (str/unicode)
                  --> id_list              ID列表 (list)(最大长度20000)
                  --> field_list           字段列表 (list)
             返回:成功返回list
             """             
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not  isinstance(field_list, list):
                raise Exception("etask_type.get argv error ,there must be (str/unicode, list, list)")          
            return tw.send_web(tw.etask_type.__name__, "get", {"db":db, "field_array":field_list, "id_array":id_list})
        
        
        @staticmethod
        def get_filter(db, field_list, filter_list):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, field_list, filter_list)
                 --> db                     数据库 (str/unicode)
                 --> field_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(field_list, list) or not isinstance(filter_list, list):
                raise Exception("etask_type.get_filter argv error, there must be(str/unicode, list, list)")   
            
            return tw.send_web(tw.etask_type.__name__, "get_filter", {"db":db, "field_array":field_list, "filter_array":filter_list})
   
    class note:  
        
        @staticmethod
        def fields(db):             
            u"""
            描述: 获取所有字段标识
            调用: fields(db)
                  --> db                    数据库 (str/unicode)
            返回: 成功返回list
            """      
            if not isinstance(db, basestring):
                raise Exception("note.fields argv error, there must be(str/unicode)")       

            return tw.send_web(tw.note.__name__, "fields", {"db":db})
                
        @staticmethod
        def get_id(db, filter_list, limit="5000"):
            u"""
             描述:获取记录id列表
             调用:get_id(db, filter_list, limit="5000")
                  --> db                      数据库 (str/unicode)
                  --> filter_list             过滤语句列表 (list)
                  --> limit                   限制条数 (str/unicode), 默认是5000
             返回: 成功返回list
             """   
            if not isinstance(db, basestring) or not isinstance(filter_list, list) or not isinstance(limit, basestring):
                raise Exception("note.get_id argv error, there must be(str/unicode, list, str/unicode)")  
            
            return tw.send_web(tw.note.__name__, "get_id", {"db":db, "filter_array":filter_list, "limit":limit})
        
        @staticmethod
        def get(db, id_list, field_list, limit="5000", order_list=[]):
            u"""
             描述:获取记录列表
             调用:get(db, id_list, field_list, limit="5000", order_list=[])
                  --> db                      数据库 (str/unicode)
                  --> id_list                 ID列表 (list)(最大长度20000)
                  --> field_list              字段列表 (list)
                  --> limit                   限制条数 (str/unicode), 默认是5000
                  --> order_list              排序列表 (list)
             返回: 成功返回list
             """                
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not isinstance(field_list, list) or \
               not isinstance(limit, basestring) or  not isinstance(order_list, list):
                raise Exception("note.get argv error, there must be(str/unicode, list, list, str/unicode, list)")              
            
            return tw.send_web(tw.note.__name__, "get", {"db":db, "field_array":field_list, "id_array":id_list, "order_field_array":order_list, "limit":limit})
        
        @staticmethod
        def get_filter(db, field_list, filter_list, limit="5000", order_list=[]):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, field_list, filter_list, limit="5000", order_list=[])
                 --> db                     数据库 (str/unicode)
                 --> field_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_list        顺序的字段标识列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(field_list, list) or not isinstance(filter_list, list)  or not isinstance(limit, basestring) or not isinstance(order_list, list) :
                raise Exception("note.get_filter argv error, there must be(str/unicode, list, list, str/unicode, list)")   
            
            return tw.send_web(tw.note.__name__, "get_filter", {"db":db, "field_array":field_list, "filter_array":filter_list, "order_field_array":order_list, "limit":limit})
                
        
        @staticmethod
        def create(db, module, module_type, link_id_list, text, cc_account_id="", image_list=[], tag_list=[], exec_event_filter=True, argv_dict={}, call_back=None):
            u"""
             描述:创建记录
             调用:create(db, module, module_type, link_id_list, text, cc_account_id="", image_list=[], tag_list=[], exec_event_filter=True)
                  --> db                      数据库 (str/unicode)
                  --> module                  模块 (str/unicode)
                  --> module_type             模块类型 (str/unicode)
                  --> link_id_list            任务的ID列表 (list)
                  --> text                    内容 (str/unicode/list) 
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                  --> cc_account_id            抄送账号ID (str/unicode), 默认为""
                  --> image_list              图片路径列表 (list), 默认为[]
                  --> tag_list                标签列表 (list),单个标签为字符串
                  --> exec_event_filter       执行事件过滤器(bool)
                  --> argv_dict               额外的数据 (dict), 格式:{key: value}
                  --> call_back               回调函数,用于计算进度, 默认为None
             返回:成功返回ID
             """                
            from twlib._note import _note
            global G_tw_http_ip
            global G_tw_token       
            t_account_id = tw.login.account_id()
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
               not isinstance(link_id_list, list) or not isinstance(text,(list,basestring)) or not isinstance(cc_account_id, basestring) or \
               not isinstance(image_list, list) or not isinstance(tag_list, list) or not isinstance(exec_event_filter,bool) or not isinstance(argv_dict, dict):
                raise Exception("note.create argv error, there must be(str/unicode, str/unicode, str/unicode, list, str/unicode, str/unicode, list, list, bool, dict)")               
            return _note.create(tw.send_web, G_tw_http_ip, G_tw_token, t_account_id, db, module, module_type, link_id_list, text, cc_account_id, image_list, tag_list, exec_event_filter, argv_dict, call_back)
        
        @staticmethod
        def create_child(db, parent_id, text, cc_account_id="", image_list=[], tag_list=[], exec_event_filter=True, call_back=None):
            u"""
             描述:创建子记录
             调用:create_child(db, parent_id, text, cc_account_id="", image_list=[], tag_list=[], exec_event_filter=True)
                  --> db                      数据库 (str/unicode)
                  --> parent_id               父noteID (str/unicode)
                  --> text                    内容 (str/unicode/list) 
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},
                                                {"type":"attachment","path":"1.txt"}]
                  --> cc_account_id            抄送账号ID (str/unicode), 默认为""
                  --> image_list              图片路径列表 (list), 默认为[]
                  --> tag_list                标签列表 (list),单个标签为字符串
                  --> exec_event_filter       执行事件过滤器(bool)
                  --> call_back               回调函数,用于计算进度, 默认为None
             返回:成功返回ID
             """                
            from twlib._note import _note
            global G_tw_http_ip
            global G_tw_token       
            if not isinstance(db, basestring) or not isinstance(parent_id, basestring) or not isinstance(text,(list,basestring)) or not isinstance(cc_account_id, basestring) or \
               not isinstance(image_list, list) or not isinstance(tag_list, list) or not isinstance(exec_event_filter,bool):
                raise Exception("note.create_child argv error, there must be(str/unicode, str/unicode, list, str/unicode, str/unicode, list, list, bool)")               
            return _note.create_child(tw.send_web, G_tw_http_ip, G_tw_token, db, parent_id, text, cc_account_id, image_list, tag_list, exec_event_filter, call_back)
        
        @staticmethod
        def set(db, id, text, tag_list=[], exec_event_filter=True, call_back=None):
            u"""
             描述:修改记录
             调用:set(db, id, text, tag_list=[], exec_event_filter=True)
                  --> db                      数据库 (str/unicode)
                  --> text                    内容 (str/unicode/list) 
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},    
                                                {"type":"attachment","path":"1.txt"}]
                  --> tag_list                标签列表 (list),单个标签为字符串
                  --> exec_event_filter       执行事件过滤器(bool)
                  --> call_back               回调函数,用于计算进度, 默认为None
             返回:成功返回True
             """                
            from twlib._note import _note
            if not isinstance(db, basestring) or not isinstance(id, basestring) or not isinstance(text,(list,basestring)) or not isinstance(tag_list, list) or not isinstance(exec_event_filter,bool):
                raise Exception("note.set argv error, there must be(str/unicode, str/unicode, str/unicode/list, list, bool)")    
            global G_tw_http_ip
            global G_tw_token    
            return _note.set(tw.send_web, G_tw_http_ip, G_tw_token, db, id, text, tag_list, exec_event_filter, call_back)        
        
        @staticmethod
        def append(db, id, text, tag_list=[], exec_event_filter=True, call_back=None):
            u"""
             描述:追加记录
             调用:append(db, id, text, tag_list=[], exec_event_filter=True)
                  --> db                      数据库 (str/unicode)
                  --> text                    内容 (str/unicode/list) 
                                                list格式,可传递文本类型text,图片类型image,链接类型a,附件类型attachment,例:
                                                [{"type":"text","content":"te"},
                                                {"type":"a","title":"aa","url":"g:/1.jpg"},
                                                {"type":"image","path":"1.jpg"},    
                                                {"type":"attachment","path":"1.txt"}]
                  --> tag_list                标签列表 (list),单个标签为字符串
                  --> exec_event_filter       执行事件过滤器(bool)
                  --> call_back               回调函数,用于计算进度, 默认为None
             返回:成功返回True
             """                
            from twlib._note import _note
            if not isinstance(db, basestring) or not isinstance(id, basestring) or not isinstance(text,(list,basestring)) or not isinstance(tag_list, list) or not isinstance(exec_event_filter,bool):
                raise Exception("note.append argv error, there must be(str/unicode, str/unicode, str/unicode/list, list, bool)")    
            global G_tw_http_ip
            global G_tw_token    
            return _note.append(tw.send_web, G_tw_http_ip, G_tw_token, db, id, text, tag_list, exec_event_filter, call_back)
   
    class filebox:
        @staticmethod
        def fields():
            u"""
             描述:获取所有字段标识
             调用:fields()
             返回:成功返回list
             """               
            return tw.send_web(tw.filebox.__name__, "fields", {})
        
        @staticmethod
        def get(db, module, module_type, field_list, pipeline_id_list):
            u"""
             描述:获取记录列表
             调用:get(db, module, module_type, field_list, pipeline_id_list)
                  --> db                      数据库(str/unicode)
                  --> module                  模块(str/unicode)
                  --> module_type             模块类型(str/unicode)
                  --> field_list              字段列表 (list)
                  --> pipeline_id_list        阶段ID列表 (list)
             返回:成功返回list
             """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or  not isinstance(module_type, basestring) or not isinstance(pipeline_id_list, list) or not isinstance(field_list, list):
                raise Exception("filebox.get argv error ,there must be (str/unicode, str/unicode, str/unicode, list, list)")             
            return tw.send_web(tw.filebox.__name__, "get", {"db":db, "module":module, "module_type":module_type, "field_array":field_list, "pipeline_id_array":pipeline_id_list})
   
    class field:
        @staticmethod
        def type():
            u"""
             描述:获取字段的所有类型
             调用:type()
             返回:成功返回list
             """               
            return tw.send_web(tw.field.__name__, "type", {})
        @staticmethod
        def create(db, module, module_type, chinese_name, english_name, sign, type, field_name=""):
            u"""
             描述:创建模块字段
             调用:create(db, module, module_type, chinese_name, english_name, sign, type, field_name="")
                  --> db                      数据库 (str/unicode)
                  --> module                  模块 (str/unicode)
                  --> module_type             模块类型 (str/unicode)
                  --> chinese_name            中文名 (str/unicode)
                  --> english_name            英文名 (str/unicode)
                  --> sign                    字段标识 (str/unicode)
                  --> type                    类型 (str/unicode)
                  --> field_name              字段名 (str/unicode), 默认为"",为空时,默认和sign一样
             返回:成功返回True
             """              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
               not isinstance(chinese_name, basestring) or not isinstance(english_name, basestring) or not isinstance(sign, basestring) or \
               not isinstance(type, basestring) or not isinstance(field_name, basestring):
                raise Exception("field.create argv error ,there must be (str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode)")   
            return tw.send_web(tw.field.__name__, "create", {"db":db, "module": module,"module_type":module_type, "chinese_name":chinese_name, "english_name":english_name, "sign":sign, "type":type, "field_name":field_name})
        @staticmethod
        def count(db, filter_list):
            u"""
            描述:统计记录条数
            调用:count(db, filter_list)
                  --> db                   数据库 (str/unicode)
                  --> filter_list          过滤语句列表 (list)
            返回:成功返回str
            """
            if not isinstance(db, basestring) or not isinstance(filter_list, list) :
                raise Exception("field.count argv error, there must be (str/unicode, list)") 
            return tw.send_web(tw.field.__name__, "count", {"db":db,'filter_list':filter_list})
        @staticmethod
        def get_filter(db, field_list, filter_list):
            u"""
            描述: 获取字段列表
            调用: get_filter(db, field_list, filter_list)
                 --> db                 数据库 (str/unicode)
                 --> field_list         字段标识列表 (list)
                 --> filter_list        过滤语句列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(field_list, list) or not isinstance(filter_list, list) :
                raise Exception("field.get_filter argv error, there must be(str/unicode, list, list)")   
            
            return tw.send_web(tw.field.__name__, "get_filter", {"db":db,  "field_array":field_list, "filter_array":filter_list})
   
    class folder:
        @staticmethod
        def get_sign(db):
            u"""
            描述:获取目录结构标识数据
            调用:get_sign(db)
                  --> db                   数据库 (str/unicode)
            返回:成功返回list
            """
            if not isinstance(db, basestring):
                raise Exception("folder.get_sign argv error, there must be (str/unicode)") 
            return tw.send_web(tw.folder.__name__, "get_sign", {"db":db, "os":_lib.get_os()})
   
    class plugin:
        
        @staticmethod
        def fields():
            u"""
             描述:获取所有字段标识
             调用:fields()
             返回:成功返回list
             """                
            return tw.send_web(tw.plugin.__name__, "fields", {})
        
        @staticmethod
        def get_id(filter_list):
            u"""
             描述:获取记录id列表
             调用:get_id(filter_list)
                  --> filter_list            过滤语句列表 (list)
             返回:成功返回list
             """                  
            if not isinstance(filter_list, list):
                raise Exception("plugin.get_id argv error ,there must be (list)") 
            
            return tw.send_web(tw.plugin.__name__, "get_id", {"filter_array":filter_list})
                    
        @staticmethod
        def get(id_list, field_list):
            u"""
             描述:获取记录列表
             调用:get(id_list, field_list)
                  --> id_list                ID列表 (list)(最大长度20000)
                  --> field_list             字段列表 (list)
             返回:成功返回list
             """         
            if not isinstance(id_list, list) or not isinstance(field_list, list):
                raise Exception("plugin.get argv error ,there must be (list, list)")             
            return tw.send_web(tw.plugin.__name__, "get", {"id_array":id_list, "field_array":field_list})
        
        @staticmethod
        def get_filter(field_list, filter_list):
            u"""
            描述: 获取记录列表
            调用: get_filter(field_list, filter_list)
                 --> field_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(field_list, list) or not isinstance(filter_list, list):
                raise Exception("plugin.get_filter argv error, there must be(list, list)")   
            
            return tw.send_web(tw.plugin.__name__, "get_filter", {"field_array":field_list, "filter_array":filter_list})
      
        
        @staticmethod
        def get_argvs(id):    
            u"""
             描述:获取指定插件所有的参数字典
             调用:get_argvs(id):  
                  --> id                    插件ID (str/unicode)
             返回:成功返回dict
             """               
            if not isinstance(id, basestring):
                raise Exception("plugin.get_argvs argv error ,there must be (str/unicode)")                   
            return tw.send_web(tw.plugin.__name__, "get_argvs", {"id":id})
        
        @staticmethod
        def set_argvs(id, argvs_dict):  
            u"""
             描述:设置插件参数
             调用:set_argvs(id, argvs_dict):  
                  --> id                    插件ID (str/unicode)
                  --> argvs_dict            更新参数 (dict), 格式{'key':'value'}
             返回:成功返回True
             """              
            if not isinstance(id, basestring) or not isinstance(argvs_dict, dict):
                raise Exception("plugin.set_argvs argv error ,there must be (str/unicode, dict)")                 
            return tw.send_web(tw.plugin.__name__, "set_argvs", {"id":id, "argv_data":argvs_dict})
   
    class pipeline:
        
        @staticmethod
        def fields():
            u"""
             描述:获取所有字段标识
             调用:fields()
             返回:成功返回list
             """   
            return tw.send_web(tw.pipeline.__name__, "fields", {})

        
        @staticmethod
        def get_id(db, filter_list):
            u"""
             描述:获取记录id列表
             调用:get_id(db, filter_list)
                  --> db                    数据库 (str/unicode)
                  --> filter_list           过滤语句列表 (list)
             返回:成功返回list
             """              
            if not isinstance(db, basestring) or not isinstance(filter_list, list):
                raise Exception("pipeline.get_id argv error ,there must be (str/unicode, list)")          
            return tw.send_web(tw.pipeline.__name__, "get_id", {"db":db, "filter_array":filter_list})
                    
        @staticmethod
        def get(db, id_list, field_list):
            u"""
             描述:获取记录列表
             调用:get(db, id_list, field_list)
                  --> db                   数据库 (str/unicode)
                  --> id_list              ID列表 (list)(最大长度20000)
                  --> field_list           字段列表 (list)
             返回:成功返回list
             """             
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not  isinstance(field_list, list):
                raise Exception("pipeline.get argv error ,there must be (str/unicode, list, list)")          
            return tw.send_web(tw.pipeline.__name__, "get", {"db":db, "field_array":field_list, "id_array":id_list})
        
        
        @staticmethod
        def get_filter(db, field_list, filter_list):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, field_list, filter_list)
                 --> db                     数据库 (str/unicode)
                 --> field_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(field_list, list) or not isinstance(filter_list, list):
                raise Exception("pipeline.get_filter argv error, there must be(str/unicode, list, list)")   
            
            return tw.send_web(tw.pipeline.__name__, "get_filter", {"db":db, "field_array":field_list, "filter_array":filter_list})
    
    class history:

        @staticmethod
        def fields(db):             
            u"""
            描述: 获取所有字段标识
            调用: fields(db)
                  --> db                    数据库 (str/unicode)
            返回: 成功返回list
            """      
            if not isinstance(db, basestring):
                raise Exception("history.fields argv error, there must be(str/unicode)")       
            return tw.send_web(tw.history.__name__, "fields", {"db":db})
        
        @staticmethod
        def get_id(db, filter_list, limit="5000"):
            u"""
             描述:获取记录id列表
             调用:get_id(db, filter_list, limit="5000")
                 --> db                    数据库 (str/unicode)
                 ---filter_list            过滤语句列表 (list)
                 --> limit                 限制条数 (str/unicode), 默认是5000
             返回:成功返回list
             """              
            if not isinstance(db, basestring) or not isinstance(filter_list, list) or not  isinstance(limit, basestring):
                raise Exception("history.get_id argv error, there must be (str/unicode, list, str/unicode)")                
            return tw.send_web(tw.history.__name__, "get_id", {"db":db, "filter_array":filter_list, "limit":limit})
                    
        @staticmethod
        def get(db, id_list, field_list, limit="5000", order_list=[], start_num=""):
            u"""
             描述:获取记录列表
             调用:get(db, id_list, field_list, limit="5000", order_list=[], start_num="")
                 --> db                    数据库 (str/unicode)
                 --> id_list               id列表 (list)(最大长度20000)
                 --> field_list            字段列表 (list)
                 --> limit                 限制条数 (str/unicode), 默认是5000
                 --> order_list            排序列表 (list), 默认为[]
                 --> start_num             开始条数 (str/unicode), 默认为""
             返回: 成功返回list
             """               
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not isinstance(field_list, list) or\
               not  isinstance(limit, basestring) or not isinstance(order_list, list) or not isinstance(start_num, basestring):
                raise Exception("history.get argv error, there must be (str/unicode, list, list, str/unicode, list, str/unicode)")                  
            return tw.send_web(tw.history.__name__, "get", {"db":db, "field_array":field_list, "id_array":id_list, "order_field_array":order_list, "limit":limit, "start_num":start_num}) 

        @staticmethod
        def get_filter(db, field_list, filter_list, limit="5000", order_list=[], start_num=""):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, field_list, filter_list, limit="5000", order_list=[], start_num="")
                 --> db                     数据库 (str/unicode)
                 --> field_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_list        顺序的字段标识列表 (list)
                 --> start_num             开始条数 (str/unicode), 默认为""
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(field_list, list) or not isinstance(filter_list, list)  or not isinstance(limit, basestring) or not isinstance(order_list, list)  or not isinstance(start_num, basestring):
                raise Exception("history.get_filter argv error, there must be(list, list, str/unicode, list, str/unicode)")   
            
            return tw.send_web(tw.history.__name__, "get_filter", {"db":db, "field_array":field_list, "filter_array":filter_list, "order_field_array":order_list, "limit":limit, "start_num":start_num})
        
        @staticmethod
        def count(db, filter_list):
            u"""
             描述:统计记录条数
             调用:count(db, filter_list)
                  --> db                   数据库 (str/unicode)
                  --> filter_list          过滤语句列表 (list)
             返回:成功返回str
             """               
            if not isinstance(db, basestring) or not isinstance(filter_list, list) :
                raise Exception("history.count argv error, there must be (str/unicode, list)")                 
            return tw.send_web(tw.history.__name__, "count", {"db":db, "filter_array":filter_list}) 
   
    class link:
        @staticmethod
        def link_asset(db, module, module_type, id_list, link_id_list, exec_event_filter=True):
            u"""
             描述:关联资产
             调用:link_asset(db, module, module_type, id_list, link_id_list, exec_event_filter=True)
                 --> db                   数据库 (str/unicode)
                 --> module               模块 (str/unicode)
                 --> module_type          模块类型 (str/unicode)
                 --> id_list              任务ID列表 (list)
                 --> link_id_list         资产ID列表 (list)
                 --> exec_event_filter    执行事件过滤器(bool)
             返回:成功返回True
             """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
               not isinstance(id_list, list) or not isinstance(link_id_list, list) or not isinstance(exec_event_filter, bool):
                raise Exception("link.link_asset argv error, there must be (str/unicode, str/unicode, str/unicode, list, list)")     
            return tw.send_web(tw.link.__name__, "link_entity", {"db":db, "module":module, "module_type":module_type, "id_array":id_list, "link_module":"asset", "link_id_array":link_id_list, "exec_event_filter":exec_event_filter}) 

        
        @staticmethod
        def link_asset_num(db, module, module_type, id_list, link_id_dict, exec_event_filter=True):
            u"""
             描述:添加关联资产的引用次数
             调用:link_asset_num(db, module, module_type, id_list, link_id_dict, exec_event_filter=True)
                 --> db                   数据库 (str/unicode)
                 --> module               模块 (str/unicode)
                 --> module_type          模块类型 (str/unicode)
                 --> id_list              任务ID列表 (list)
                 --> link_id_dict         资产ID字典 (dict),如{asset_id: num}
                 --> exec_event_filter    执行事件过滤器(bool)
             返回:成功返回True
             """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
               not isinstance(id_list, list) or not isinstance(link_id_dict, dict)  or not isinstance(exec_event_filter, bool):
                raise Exception("link.link_asset_num argv error, there must be (str/unicode, str/unicode, str/unicode, list, dict)")    
            return tw.send_web(tw.link.__name__, "link_entity_num", {"db":db, "module":module, "module_type":module_type, "id_array":id_list, "link_module":"asset", "link_data":link_id_dict, "exec_event_filter":exec_event_filter}) 

        @staticmethod
        def unlink_asset(db, module, module_type, id_list, link_id_list, exec_event_filter=True):
            u"""
             描述:取消关联的资产
             调用:unlink_asset(db, module, module_type, id_list, link_id_list, exec_event_filter=True)
                 --> db                  数据库 (str/unicode)
                 --> module              模块 (str/unicode)
                 --> module_type         模块类型 (str/unicode)
                 --> id_list             任务ID列表 (list)
                 --> link_id_list        资产ID列表 (list)
                 --> exec_event_filter   执行事件过滤器(bool)
             返回:成功返回True
             """          
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
                       not isinstance(id_list, list) or not isinstance(link_id_list, list)  or not isinstance(exec_event_filter, bool):
                raise Exception("link.unlink_asset argv error, there must be (str/unicode, str/unicode, str/unicode, list, list)")
            return tw.send_web(tw.link.__name__, "unlink_entity", {"db":db, "module":module, "module_type":module_type, "id_array":id_list, "link_module":"asset", "link_id_array":link_id_list, "exec_event_filter":exec_event_filter}) 
    

        @staticmethod
        def get_asset(db, module, module_type, id):
            u"""
             描述:获取关联资产的id和引用次数的字典
             调用:get_asset(db, module, module_type, id)
                 --> db                 数据库 (str/unicode)
                 --> module             模块 (str/unicode)
                 --> module_type        模块类型 (str/unicode)
                 --> id                 任务ID (str/unicode)
             返回:成功返回字典:{资产id:引用次数,资产id:引用次数,...}
             """               
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
                       not isinstance(id, basestring):
                raise Exception("link.get_asset argv error, there must be (str/unicode, str/unicode, str/unicode, str/unicode)")     
            return tw.send_web(tw.link.__name__, "get_entity", {"db":db, "module":module, "module_type":module_type, "id":id, "link_module":"asset"}) 

        @staticmethod
        def link_entity(db, module, module_type, id_list, link_module, link_id_list, exec_event_filter=True):
            u"""
             描述:关联模块记录
             调用:link_entity(db, module, module_type, id_list, link_module, link_id_list, exec_event_filter=True)
                 --> db                   数据库 (str/unicode)
                 --> module               模块 (str/unicode)
                 --> module_type          模块类型 (str/unicode)
                 --> id_list              任务ID列表 (list)
                 --> link_module          link模块标识(str/unicode)
                 --> link_id_list         资产ID列表 (list)
                 --> exec_event_filter    执行事件过滤器(bool)
             返回:成功返回True
             """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
               not isinstance(id_list, list) or not isinstance(link_id_list, list) or not isinstance(link_module, basestring) or not isinstance(exec_event_filter, bool):
                raise Exception("link.link_entity argv error, there must be (str/unicode, str/unicode, str/unicode, list, str/unicode, list)")     
            return tw.send_web(tw.link.__name__, "link_entity", {"db":db, "module":module, "module_type":module_type, "id_array":id_list, "link_module":link_module, "link_id_array":link_id_list, "exec_event_filter":exec_event_filter}) 

        @staticmethod
        def link_entity_num(db, module, module_type, id_list, link_module, link_id_dict, exec_event_filter=True):
            u"""
             描述:添加关联模块的引用次数
             调用:link_entity_num(db, module, module_type, id_list, link_module, link_id_dict, exec_event_filter=True)
                 --> db                   数据库 (str/unicode)
                 --> module               模块 (str/unicode)
                 --> module_type          模块类型 (str/unicode)
                 --> id_list              任务ID列表 (list)
                 --> link_module          link模块标识(str/unicode)
                 --> link_id_dict         资产ID字典 (dict),如{asset_id: num}
                 --> exec_event_filter    执行事件过滤器(bool)
             返回:成功返回True
             """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
               not isinstance(id_list, list) or not isinstance(link_id_dict, dict) or not isinstance(link_module, basestring)  or not isinstance(exec_event_filter, bool):
                raise Exception("link.link_entity_num argv error, there must be (str/unicode, str/unicode, str/unicode, list, str/unicode, dict)")    
            return tw.send_web(tw.link.__name__, "link_entity_num", {"db":db, "module":module, "module_type":module_type, "id_array":id_list, "link_module":link_module, "link_data":link_id_dict, "exec_event_filter":exec_event_filter}) 
        
        @staticmethod
        def unlink_entity(db, module, module_type, id_list, link_module, link_id_list, exec_event_filter=True):
            u"""
             描述:取消关联模块的记录
             调用:unlink_entity(db, module, module_type, id_list, link_module, link_id_list, exec_event_filter=True)
                 --> db                  数据库 (str/unicode)
                 --> module              模块 (str/unicode)
                 --> module_type         模块类型 (str/unicode)
                 --> id_list             任务ID列表 (list)
                 --> link_module         link模块标识(str/unicode)
                 --> link_id_list        资产ID列表 (list)
                 --> exec_event_filter   执行事件过滤器(bool)
             返回:成功返回True
             """          
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
                       not isinstance(id_list, list) or not isinstance(link_id_list, list) or not isinstance(link_module, basestring) or not isinstance(exec_event_filter, bool):
                raise Exception("link.unlink_entity argv error, there must be (str/unicode, str/unicode, str/unicode, list, list)")
            return tw.send_web(tw.link.__name__, "unlink_entity", {"db":db, "module":module, "module_type":module_type, "id_array":id_list, "link_module":link_module, "link_id_array":link_id_list, "exec_event_filter":exec_event_filter}) 


        @staticmethod
        def get_entity(db, module, module_type, id, link_module):
            u"""
             描述:获取关联模块的id和引用次数的字典
             调用:get_entity(db, module, module_type, id, link_module)
                 --> db                 数据库 (str/unicode)
                 --> module             模块 (str/unicode)
                 --> module_type        模块类型 (str/unicode)
                 --> link_module        link模块标识(str/unicode)
                 --> id                 任务ID (str/unicode)
             返回:成功返回字典:{资产id:引用次数,资产id:引用次数,...}
             """               
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
                       not isinstance(id, basestring)  or not isinstance(link_module, basestring):
                raise Exception("link.get_entity argv error, there must be (str/unicode, str/unicode, str/unicode, str/unicode, str/unicode)")       
            return tw.send_web(tw.link.__name__, "get_entity", {"db":db, "module":module, "module_type":module_type, "id":id, "link_module":link_module}) 

        @staticmethod
        def reset_link_asset_num(db, module, module_type, id_list, link_id_dict, exec_event_filter=True):
            u"""
             描述:重置关联资产的引用次数
             调用:reset_link_asset_num(db, module, module_type, id_list, link_id_dict, exec_event_filter=True)
                 --> db                   数据库 (str/unicode)
                 --> module               模块 (str/unicode)
                 --> module_type          模块类型 (str/unicode)
                 --> id_list              任务ID列表 (list)
                 --> link_id_dict         资产ID字典 (dict),如{asset_id: num}
                 --> exec_event_filter   执行事件过滤器(bool)
             返回:成功返回True
             """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
               not isinstance(id_list, list) or not isinstance(link_id_dict, dict)  or not isinstance(exec_event_filter, bool):
                raise Exception("link.set_link_asset_num argv error, there must be (str/unicode, str/unicode, str/unicode, list, dict)") 
            return tw.send_web(tw.link.__name__, "reset_link_num", {"db":db, "module":module, "module_type":module_type, "id_array":id_list, "link_module":"asset", "link_data":link_id_dict, "exec_event_filter":exec_event_filter}) 
        
        @staticmethod
        def reset_link_entity_num(db, module, module_type, id_list, link_module, link_id_dict, exec_event_filter=True):
            u"""
             描述:重置关联模块的引用次数
             调用:reset_link_entity_num(db, module, module_type, id_list, link_module, link_id_dict, exec_event_filter=True)
                 --> db                   数据库 (str/unicode)
                 --> module               模块 (str/unicode)
                 --> module_type          模块类型 (str/unicode)
                 --> id_list              任务ID列表 (list)
                 --> link_module          link模块标识(str/unicode)
                 --> link_id_dict         资产ID字典 (dict),如{asset_id: num}
                 --> exec_event_filter   执行事件过滤器(bool)
             返回:成功返回True
             """             
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
               not isinstance(id_list, list) or not isinstance(link_id_dict, dict) or not isinstance(link_module, basestring) or not isinstance(exec_event_filter, bool):
                raise Exception("link.reset_link_entity_num argv error, there must be (str/unicode, str/unicode, str/unicode, list, str/unicode, dict)")    
            return tw.send_web(tw.link.__name__, "reset_link_num", {"db":db, "module":module, "module_type":module_type, "id_array":id_list, "link_module":link_module, "link_data":link_id_dict, "exec_event_filter":exec_event_filter}) 
    
    class software:

        @staticmethod
        def types():
            u"""
             描述:获取软件类型
             调用:types()
             返回:成功返回list
             """               
            return tw.send_web(tw.software.__name__, "types", {}) 

        
        @staticmethod
        def get_path(db, name):
            u"""
             描述:获取软件路径
             调用:get_path(db, name):
                  --> db                数据库 (str/unicode)
                  --> name              软件名称 (str/unicode)
             返回:成功返回str
             """       
            if not isinstance(db, basestring) or not isinstance(name, basestring) :
                raise Exception("software.get_path argv error, there must be (str/unicode, str/unicode)")               
            return tw.send_web(tw.software.__name__, "get_path", {"db":db, "name":name, "os":_lib.get_os()})     
            
        @staticmethod
        def get_with_type(db, type):
            u"""
             描述: 根据类型获取软件信息
             调用: get_with_type(db, type):
                  --> db                数据库 (str/unicode)
                  --> type              软件类型 (str/unicode)
             返回: 成功返回str
             """   
            if not isinstance(db, basestring) or not isinstance(type, basestring) :
                raise Exception("software.get_with_type argv error, there must be (str/unicode, str/unicode)")                 
            return tw.send_web(tw.software.__name__, "get_with_type", {"db":db, "type":type, "os":_lib.get_os()})   
    
    class api_data:

        @staticmethod
        def get(db, key, is_user=True):
            u"""
             描述:获取项目自定义数据
             调用:get(db, key, is_user=True)
                  --> db                数据库 (str/unicode)
                  --> key               键 (str/unicode)
                  --> is_user           是否为个人 (bool), 默认为True
                  
             返回:成功返回str
             """             
            if not isinstance(db, basestring) or not isinstance(key, basestring) or not isinstance(is_user, bool):
                raise Exception("api_data.get argv error, there must be (str/unicode, str/unicode, bool)")   
            return tw.send_web(tw.api_data.__name__, "get", {"db":db, "key":key, "is_user":is_user})
        
        @staticmethod
        def set(db, key, value, is_user=True):
            u"""
             描述:设置项目自定义数据
             调用:set(db, key, value, is_user=True)
                  --> db                数据库 (str/unicode)
                  --> key               键 (str/unicode)
                  --> value             值 (str/unicode)
                  --> is_user           是否为个人 (bool), 默认为True
                  
             返回:成功返回True
             """                 
            if not isinstance(db, basestring) or not isinstance(key, basestring) or not isinstance(value, basestring) or\
               not isinstance(is_user, bool):
                raise Exception("api_data.set argv error, there must be (str/unicode, str/unicode, str/unicode, bool)")                
            return tw.send_web(tw.api_data.__name__, "set", {"db":db, "key":key, "value":value, "is_user":is_user})
    
    class version:
        
        @staticmethod
        def fields(db):             
            u"""
            描述: 获取所有字段标识
            调用: fields(db)
                  --> db                    数据库 (str/unicode)
            返回: 成功返回list
            """      
            if not isinstance(db, basestring):
                raise Exception("version.fields argv error, there must be(str/unicode)")      
            return tw.send_web(tw.version.__name__, "fields", {"db":db})
        
        @staticmethod
        def get_id(db, filter_list, limit="5000"):
            u"""
            描述: 获取记录id列表
            调用: get_id(db, filter_list, limit="5000")
                 --> db                      数据库 (str/unicode)
                 --> filter_list             过滤语句列表 (list)
                 --> limit                   限制条数 (str/unicode), 默认是5000
            返回: 成功返回list
            """       
            if not isinstance(db, basestring) or not isinstance(filter_list, list) or \
               not isinstance(limit, basestring):
                raise Exception("verson.get_id argv error, there must be(str/unicode, list, str/unicode)")  
            return tw.send_web(tw.version.__name__, "get_id", {"db":db, "filter_array":filter_list, "limit":limit})
                    
        @staticmethod
        def get(db, id_list, field_list, limit="5000", order_list=[]):
            u"""
            描述: 获取记录列表
            调用: get(db, id_list, field_list, limit="5000", order_list=[])
                 --> db                     数据库 (str/unicode)
                 --> id_list                ID列表 (list)(最大长度20000)
                 --> field_list             字段列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_list        顺序的字段标识列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(id_list, list) or \
               not isinstance(field_list, list)  or not isinstance(limit, basestring) or not isinstance(order_list, list):
                raise Exception("verson.get argv error, there must be(str/unicode, list, list, str/unicode, list)")   
            return tw.send_web(tw.version.__name__, "get", {"db":db, "field_array":field_list, "id_array":id_list, "order_field_array":order_list, "limit":limit})
        
        @staticmethod
        def get_filter(db, field_list, filter_list, limit="5000", order_list=[]):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, field_list, filter_list, limit="5000", order_list=[])
                 --> db                     数据库 (str/unicode)
                 --> field_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_list        顺序的字段标识列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(field_list, list) or not isinstance(filter_list, list)  or not isinstance(limit, basestring) or not isinstance(order_list, list) :
                raise Exception("version.get_filter argv error, there must be(str/unicode, list, list, str/unicode, list)")   
            
            return tw.send_web(tw.version.__name__, "get_filter", {"db":db, "field_array":field_list, "filter_array":filter_list, "order_field_array":order_list, "limit":limit})        
    
        @staticmethod
        def create(db, link_id, sign,  argv_dict={}, exec_event_filter=False):
            u"""
            描述: 创建记录
            调用: create(db, link_id, sign, argv_dict={}, exec_event_filter=False)
                 --> db                     数据库 (str/unicode)
                 --> link_id                任务ID (str/unicode)
                 --> sign                   标识 (str/unicode)
                 --> argv_dict              额外的数据 (dict), 格式:{key: value}
                 --> exec_event_filter      执行事件过滤器(bool)
            返回: 成功返回ID
            """          
            if not isinstance(db, basestring) or not isinstance(link_id, basestring)  or not isinstance(link_id, basestring) or not isinstance(argv_dict, dict) or not isinstance(exec_event_filter, bool) :
                raise Exception("version.create argv error, there must be(str/unicode, str/unicode, str/unicode, dict, bool)") 
            return tw.send_web(tw.version.__name__, "create", {"db":db, "link_id":link_id, "sign":sign, "field_data_array":argv_dict, "exec_event_filter":exec_event_filter})
    
    class link_entity:
        
        @staticmethod
        def get_entity(db, module, module_type, link_id):
            u"""
             描述:获取关联的实体名称
             调用:get_entity(db, module, module_type, link_id)
                  --> db                数据库 (str/unicode)
                  --> module            模块 (str/unicode)
                  --> module_type       模块类型 (str/unicode)
                  --> link_id           关联任务的ID (str/unicode)
             返回:成功返回str
             """ 
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or not isinstance(link_id, basestring) :
                raise Exception("link_entity.get_entity argv error, there must be (str/unicode, str/unicode, str/unicode, str/unicode)")    
            return tw.send_web(tw.link_entity.__name__, "get_entity", {"db":db, "module":module, "module_type":module_type, "link_id":link_id})
        
        @staticmethod
        def get(db, module, module_type, filter_entity, is_mytask=False):
            u"""
             描述:获取记录列表
             调用:get(db, module, module_type, filter_entity, is_mytask=False)
                  --> db                数据库 (str/unicode)
                  --> module            模块 (str/uicode)
                  --> module_type       模块类型 (str/unicode)
                  --> filter_entity     查找的实体 (str/unicode)
                  --> is_mytask         是否查找我的任务 bool
             返回:成功返回{id:实体名称,id:实体名称,...}
             """              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or not isinstance(filter_entity, basestring) or not isinstance(is_mytask, bool) :
                raise Exception("link_entity.get argv error, there must be (str/unicode, str/unicode, str/unicode, str/unicode, bool)")            
            return tw.send_web(tw.link_entity.__name__, "get", {"db":db, "module":module, "module_type":module_type, "filter_entity":filter_entity, "is_mytask":is_mytask})
    
    class timelog:
        
        @staticmethod
        def fields():
            u"""
             描述:获取所有字段标识
             调用:fields()
             返回:成功返回list
             """               
            return tw.send_web(tw.timelog.__name__, "fields", {})
        
        @staticmethod
        def get_id(db, filter_list, limit="5000"):
            u"""
             描述:获取记录id列表
             调用:get_id(db, filter_list, limit="5000")
                  --> db               数据库 (str/unicode)
                  --> filter_list      过滤语句 (list)
                  --> limit            限制条数 (str/unicode), 默认是5000
             返回:成功返回list
             """                
            if not isinstance(db, basestring) or not isinstance(filter_list, list) or not isinstance(limit, basestring):
                raise Exception("timelog.get_id argv error, there must be (str/unicode, list, str/unicode)")                
            return tw.send_web(tw.timelog.__name__, "get_id", {"db":db, "filter_array":filter_list, "limit":limit})
        
        @staticmethod
        def get(db, id_list, field_list, limit="5000", order_list=[]):
            u"""
             描述:获取记录列表
             调用:get(db, id_list, field_list, limit="5000", order_list=[])
                  --> db               数据库 (str/unicode)
                  --> id_list          ID列表  (list)(最大长度20000)
                  --> field_list       字段列表 (list)
                  --> limit            限制条数 (str/unicode), 默认是5000
                  --> order_list       排序列表 (list),默认为空
             返回:成功返回list
             """               
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not isinstance(field_list, list) or \
               not isinstance(limit, basestring) or  not isinstance(order_list, list):
                raise Exception("timelog.get argv error, there must be (str/unicode, list, list, str/unicode, list)")                
            return tw.send_web(tw.timelog.__name__, "get", {"db":db, "field_array":field_list, "id_array":id_list, "order_field_array":order_list, "limit":limit})
        
    
        @staticmethod
        def create(db, link_id, module, module_type, use_time, date, text, tag="", exec_event_filter=True):
            u"""
             描述:创建记录
             调用:create(db, link_id, module, module_type, use_time, date, text, tag="", exec_event_filter=True)
                  --> db                数据库 (str/unicode)
                  --> link_id           关联的任务ID (str/unicode)
                  --> module            模块 (str/unicode)
                  --> module_type       模块类型 (str/unicode)
                  --> use_time          用时 (str/unicode)格式:时:分,例 02:30
                  --> date              日期 (str/unicode)
                  --> text              内容 (unicode)
                  --> tag               标签 (unicode), 多个以逗号隔开
                  --> exec_event_filter 执行事件过滤器(bool)
             返回:成功返回ID
             """             
            if not isinstance(db, basestring) or not isinstance(link_id, basestring) or not isinstance(module, basestring) or \
               not isinstance(module_type, basestring) or not  isinstance(use_time, basestring) or not isinstance(date, basestring) or \
               not isinstance(text, basestring) or not isinstance(tag, basestring) or not isinstance(exec_event_filter, bool):
                raise Exception("timelog.create argv error, there must be (str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, unicode, bool)")                 
            return tw.send_web(tw.timelog.__name__, "create", {"db":db, "link_id":link_id, "module":module, "module_type":module_type, "use_time":use_time, "date":date, "text":text, "tag":tag, "exec_event_filter":exec_event_filter})

        @staticmethod
        def set(db, id, data_dict, exec_event_filter=True):        
            u"""
             描述:更新单条记录
             调用:set(db, id, data_dict, exec_event_filter=True)
                  --> db                数据库 (str/unicode)
                  --> id                ID (str/unicode)
                  --> data_dict         更新的数据 (dict)
                  --> exec_event_filter 执行事件过滤器(bool)
             返回:成功返回True
             """             
            if not isinstance(db, basestring) or not isinstance(id, basestring) or not isinstance(data_dict, dict) or not isinstance(exec_event_filter, bool):
                raise Exception("timelog.set_one argv error, there must be (str/unicode, str/unicode, dict, bool)")                 
            return tw.send_web(tw.timelog.__name__, "set", {"db":db, "id":id, "field_data_array":data_dict, "exec_event_filter":exec_event_filter})
    
    class flow:
        @staticmethod
        def get_data(db, pipeline_id_list):
            u"""
             描述:获取审核流程记录列表
             调用:get_data(db, pipeline_id_list)
                  --> db                 数据库 (str/unicode)
                  --> pipeline_id_list   阶段ID列表  (list)

             返回:成功返回list
             """               
            if not isinstance(db, basestring) or not isinstance(pipeline_id_list, list) :
                raise Exception("flow.get_data argv error, there must be (str/unicode, list)")      
            return tw.send_web(tw.flow.__name__, "get_data", {"db":db, "pipeline_id_array":pipeline_id_list})
        @staticmethod
        def get_node(db, flow_id):
            u"""
             描述:获取审核节点数据
             调用:get_data(db, flow_id)
                  --> db        数据库 (str/unicode)
                  --> flow_id   流程ID (str/unicode)

             返回:成功返回list
             """               
            if not isinstance(db, basestring) or not isinstance(flow_id, basestring) :
                raise Exception("flow.get_node argv error, there must be (str/unicode, str/unicode)")      
            return tw.send_web(tw.flow.__name__, "get_node", {"db":db, "flow_id":flow_id})
    
    class media_file:
        @staticmethod
        def download(db, online_path_list, des_path_list, call_back=None, backup_dir=""):
            u"""
            描述: 下载在线文件,只支持下载文件,暂不支持下载目录
            调用: download(db, online_path_list,  des_path_list, call_back=None, backup_dir="") 
                 --> db                       数据库 (str/unicode)
                 --> online_path_list         在线文件列表
                 --> des_path_list            下载存放的目标路径列表（个数和des_path_list对应）
                 --> call_back                 回调函数,用于计算进度, 默认为None
                 --> backup_dir                备份目录, 用于下载时已存在文件备份
            返回: 成功返回True
            """
            global G_tw_http_ip
            global G_tw_token
            from twlib._media_file import _media_file

            if not isinstance(db, basestring) or not isinstance(online_path_list, list) or not isinstance(des_path_list, list) or not isinstance(backup_dir, basestring):  
                raise Exception("media_file.download argv error(str/unicode, list, list)")

            if len(online_path_list) != len(des_path_list):
                raise Exception("media_file.download the number of source and destination paths does not match")


            return _media_file.download(tw.send_web, G_tw_http_ip, G_tw_token, db, online_path_list, des_path_list, call_back, backup_dir)


        @staticmethod
        def upload(db, sou_path_list, online_path_list, call_back=None, metadata={}, file_log_dict={}, folder_data={}):
            u"""
            描述: 上传到在线文件,只支持上传文件,暂不支持上传目录
            调用: upload(db, sou_path_list, online_path_list, call_back=None, metadata={}, file_log_dict={})
                 --> db                       数据库 (str/unicode)
                 --> sou_path_list            源文件列表 (list)
                 --> online_path_list         目标件列表 (list)
                 --> call_back                回调函数,用于计算进度, 默认为None
                 --> metadata                 存放自定义内容
                 --> file_log_dict            已提交的版本文件的数据,{online_path : file_id}
                 --> folder_data              目录数据(修改网盘时间) {online_dir: 2023-10-27 11:11:11,..}
            返回: 成功返回True
            """
            global G_tw_http_ip
            global G_tw_token
            from twlib._media_file import _media_file

            if not isinstance(db, basestring) or not isinstance(sou_path_list, list) or not isinstance(online_path_list, list) \
                or not isinstance(metadata, dict) or not isinstance(file_log_dict, dict) or not isinstance(folder_data, dict):
                raise Exception("media_file.upload argv error(str/unicode, list, list, dict, dict, dict)")

            if len(sou_path_list) != len(online_path_list):
                raise Exception("media_file.upload the number of source and destination paths does not match")

            return _media_file.upload(tw.send_web, G_tw_http_ip, G_tw_token, db, sou_path_list, online_path_list, call_back, metadata, file_log_dict, folder_data)
        

        
        @staticmethod
        def delete(db, online_file_list, online_dir_list=[]):
            u"""
            描述: 删除在线文件
            调用: delete(db, online_file_list, online_dir_list=[])
                 --> db                       数据库 (str/unicode)
                 --> online_file_list         目标文件列表 (list)
                 --> online_dir_list          目标目录列表 (list)
            返回: 成功返回True
            """
            if not isinstance(db, basestring) or not isinstance(online_file_list, list) or not isinstance(online_dir_list, list):
                raise Exception("media_file.delete argv error(str/unicode, list, list)")
            return tw.send_web(tw.media_file.__name__, "delete", {"db": db, "file_array":online_file_list, "dir_array":online_dir_list})
        
                
        @staticmethod
        def download_filebox(db, module, module_type, task_id, filebox_id, is_download_all=True, is_show_exist=False, call_back=None,  des_dir="", argv_dict={}):
            u"""
            描述: 下载在线文件
            调用: download_filebox(db, module, module_type, task_id, filebox_id, is_download_all=True, is_show_exist=True, call_back=None, des_dir="", argv_dict={})
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> module_type             模块类型 (str/unicode)
                 --> task_id                 任务ID (str/unicode)
                 --> filebox_id              文件框ID (str/unicode)
                 --> is_download_all         是否下载所有(bool), 默认为True, 为False下载最大版本   L为同名版本最新文件
                 --> is_show_exist           是否显示已经下载过的, 默认为False
                 --> call_back               回调函数,用于计算进度, 默认为None
                 --> des_dir                 下载存放的目标路径(保存目录结构)                                                                      
                 --> argv_dict               其他参数(dict)
            返回: 成功返回list
            """             
            global G_tw_http_ip
            global G_tw_token
            from twlib._media_file import _media_file
            if not isinstance(is_download_all,bool) and str(is_download_all).lower().strip() not in ['l','n','y']:
                raise Exception("media_file.download_filebox is_download_all argv error. ")
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or not  isinstance(task_id, basestring) or \
               not isinstance(filebox_id, basestring) or not isinstance(is_download_all, (bool,basestring)) or not isinstance(is_show_exist, bool) or not isinstance(des_dir, basestring) or not isinstance(argv_dict,dict): 
                raise Exception("media_file.download_filebox argv error(str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, bool/str/unicode, bool, None/function, str/unicode, dict)")  #--20190122 des_dir                   
            return _media_file.download_filebox(tw.send_web, G_tw_http_ip, G_tw_token, db, module, module_type, task_id, filebox_id, is_download_all, is_show_exist, des_dir, call_back, argv_dict) #--20190122 des_dir
        
        @staticmethod
        def upload_filebox(db, module, module_type, task_id, filebox_id, sou_path_list, call_back=None, argv_dict={}):
            u"""
            描述: 上传到在线文件,不会进行转码
            调用: upload_filebox(db, module, module_type, task_id, filebox_id, sou_path_list, call_back=None, argv_dict={})
                 --> db                      数据库 (str/unicode)
                 --> module                  模块 (str/unicode)
                 --> module_type             模块类型 (str/unicode)
                 --> task_id                 任务ID (str/unicode)
                 --> filebox_id              文件框ID (str/unicode)
                 --> sou_path_list           源文件列表 (list)
                 --> call_back               回调函数,用于计算进度, 默认为None
                 --> argv_dict               其他参数(dict)
            返回: 成功返回True
            """             
            global G_tw_http_ip
            global G_tw_token
            from twlib._media_file import _media_file
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or not  isinstance(task_id, basestring) or \
                       not isinstance(filebox_id, basestring) or not isinstance(sou_path_list, list) or not isinstance(argv_dict, dict):
                raise Exception("media_file.upload_filebox argv error(str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, list, dict)")              
            return _media_file.upload_filebox(tw.send_web, G_tw_http_ip, G_tw_token, db, module, module_type, task_id, filebox_id, sou_path_list, call_back, argv_dict)   
    

        @staticmethod
        def download_lastest(db, online_dir, des_dir, time, call_back=None):
            u"""
            描述: 下载指定目录下某个时间后更新的文件
            调用: download_lastest(db, online_dir, des_dir, time, call_back=None)
                 --> db                       数据库 (str/unicode)
                 --> online_dir               在线文件的目录(str/unicode)   如: /big/shot/ep01
                 --> des_dir                  保存的目录(str/unicode) 
                 --> time                     下载的起始时间(str/unicode)   格式为: 2019-01-02 00:00:22
                 --> call_back                回调函数,用于计算进度, 默认为None
            返回: 成功返回List
            """
            global G_tw_http_ip
            global G_tw_token
            from twlib._media_file import _media_file

            if not isinstance(db, basestring) or not isinstance(online_dir, basestring) or not isinstance(des_dir, basestring) or not isinstance(time, basestring) :
                raise Exception("media_file.download_lastest argv error(str/unicode, str/unicode, str/unicode, str/unicode)")

            return _media_file.download_lastest(tw.send_web, G_tw_http_ip, G_tw_token, db, online_dir, des_dir, time, call_back)  
    
    class server:
        @staticmethod
        def fields():
            u"""
             描述:获取所有字段标识
             调用:fields()
             返回:成功返回list
             """               
            return tw.send_web(tw.server.__name__, "fields", {})
        
        @staticmethod
        def get(db, field_list):
            u"""
             描述:获取信息
             调用:get(db, field_list)
                  --> db               数据库 (str/unicode)
                  --> field_list       字段列表 (list)
             返回:成功返回list
             """               
            if not isinstance(db, basestring) or not isinstance(field_list, list):
                raise Exception("server.get argv error, there must be (str/unicode, list)")                
            return tw.send_web(tw.server.__name__, "get", {"db":db, "field_array":field_list})       
        
        @staticmethod
        def get_path(db, id, os=""):
            u"""
             描述:获取指定软件路径
             调用:get_path(db, id, os="")
                  --> db               数据库 (str/unicode)
                  --> id               server的ID(str/unicode)
                  --> os               系统平台 (str/unicode),默认是当前系统平台
                  
             返回:成功返回str
             """             
            if not isinstance(db, basestring)  or not isinstance(id, basestring) or not isinstance(os, basestring) :
                raise Exception("server.get_path argv error, there must be (str/unicode, str/unicode, str/unicode)")  
            os = _lib.get_os() if os.strip() == "" else os               
            return tw.send_web(tw.server.__name__, "get_path", {"db":db, "id":id, "os":os})    
    
    class file:
        @staticmethod
        def fields(db):             
            u"""
            描述: 获取所有字段标识
            调用: fields(db)
                  --> db                    数据库 (str/unicode)
            返回: 成功返回list
            """      
            if not isinstance(db, basestring):
                raise Exception("file.fields argv error, there must be(str/unicode)")   
            return tw.send_web(tw.file.__name__, "fields", {'db':db})
        
        @staticmethod
        def create(db, module, module_type, link_id, version_id, path, is_upload_online=False, argv_dict={}):
            u"""
             描述:创建记录
             调用:create(db, module, module_type, link_id, version_id, path, is_upload_online=False, argv_dict={})
                  --> db                    数据库 (str/unicode)
                  --> module                模块 (str/unicode)
                  --> module_type           模块类型 (str/unicode)
                  --> link_id               关联的任务ID(str/unicode), 如task_id
                  --> version_id            版本ID (str/unicode)
                  --> path                  文件路径 (str)
                  --> is_upload_online      是否上传到网盘(bool)
                  --> argv_dict             自定义的数据 (dict), 格式:{key: value}
             返回:成功返回True
             """              
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(module_type, basestring) or \
                    not isinstance(link_id, basestring) or not isinstance(version_id, basestring) or not isinstance(path, basestring) \
                    or not isinstance(is_upload_online, bool) or not isinstance(argv_dict, dict):
                raise Exception("_file.create argv error,  must be( str,str,str,str,str,str,bool,dict)")        
            
            from twlib._file import _file
            return _file.create(tw.send_web, G_tw_http_ip, G_tw_token, db, module, module_type, link_id, version_id, path, is_upload_online, argv_dict)
        
        @staticmethod
        def get_id(db, filter_list, limit="5000"):
            u"""
             描述:获取记录id列表
             调用:get_id(db, filter_list, limit="5000")
                  --> db                    数据库 (str/unicode)
                  --> filter_list           过滤语句列表 (list)
                  --> limit                 限制条数 (str/unicode), 默认是5000
             返回:成功返回list
             """              
            if not isinstance(db, basestring) or not isinstance(filter_list, list):
                raise Exception("file.get_id argv error ,there must be (str/unicode, list)")     
            return tw.send_web(tw.file.__name__, "get_id", {"db":db, "filter_array":filter_list, "limit":limit})

                    
        @staticmethod
        def get(db, id_list, field_list, limit="5000", order_list=[]):
            u"""
             描述:获取记录列表
             调用:get(db, id_list, field_list, limit="5000", order_list=[])
                  --> db               数据库 (str/unicode)
                  --> id_list          ID列表  (list)(最大长度20000)
                  --> field_list       字段列表 (list)
                  --> limit            限制条数 (str/unicode), 默认是5000
                  --> order_list       排序列表 (list),默认为空
             返回:成功返回list
             """               
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not isinstance(field_list, list) or \
               not isinstance(limit, basestring) or  not isinstance(order_list, list):
                raise Exception("file.get argv error, there must be (str/unicode, list, list, str/unicode, list)")             
            return tw.send_web(tw.file.__name__, "get", {"db":db, "field_array":field_list, "id_array":id_list, "order_field_array":order_list, "limit":limit})
        
        @staticmethod
        def get_filter(db, field_list, filter_list, limit="5000", order_list=[]):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, field_list, filter_list, limit="5000", order_list=[])
                 --> db                     数据库 (str/unicode)
                 --> field_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_list        顺序的字段标识列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(field_list, list) or not isinstance(filter_list, list)  or not isinstance(limit, basestring) or not isinstance(order_list, list) :
                raise Exception("file.get_filter argv error, there must be(str/unicode, list, list, str/unicode, list)")   
            
            return tw.send_web(tw.file.__name__, "get_filter", {"db":db, "field_array":field_list, "filter_array":filter_list, "order_field_array":order_list, "limit":limit})        
        
        @staticmethod
        def delete(db, id_list):
            u"""
            描述: 删除记录
            调用: delete(db, id_list)
                 --> db                      数据库 (str/unicode)
                 --> id_list                 ID列表 (list)
            返回: 成功返回True
            """             
            if not isinstance(db, basestring) or not isinstance(id_list, list):
                raise Exception("file.delete argv error, there must be(str/unicode, list)")  
            return tw.send_web(tw.file.__name__, "delete", {"db":db, "id_array":id_list})
    
    class msg_queue:
        @staticmethod
        def create(app_key, argv_dict, timeout=10*60):
            u"""
             描述:创建消息队列任务, 一般和任务处理脚本配合使用
             调用:create(app_key, argv_dict, timeout=10*60)
                  --> app_key               程序标识(str/unicode)
                  --> argv_dict             任务的数据(dict), 格式:{key: value}
                  --> timeout               超时时长, (int)单位为秒
             返回:成功返回True
             """     
            if not isinstance(app_key, basestring) or not isinstance(argv_dict, dict)  or not isinstance(timeout, int):
                raise Exception("msg_queue.create argv error, there must be(str/unicode, dict, int)")              
            return tw.send_web(tw.msg_queue.__name__, "add", {"app_key": app_key, "argv":argv_dict, "timeout":timeout})
        
        @staticmethod
        def get(app_key):
            u"""
             描述:获取消息队列任务
             调用:get(app_key)
                  --> app_key               程序标识(str/unicode)
             返回:成功返回[]
             """     
            if not isinstance(app_key, basestring):
                raise Exception("msg_queue.get argv error, there must be(str/unicode)")              
            return tw.send_web(tw.msg_queue.__name__, "get", {"app_key": app_key})
    
    class asset_lib:
        
        @staticmethod
        def upload_asset(lib_sign, local_asset_path, online_asset_path, call_back=None): 
            u"""
            描述: 上传资产包到资产库
            调用: upload_asset(lib_sign, local_asset_path, online_asset_path, call_back=None)
                 --> lib_sign                   库标识 (str/unicode), 如lib_asset
                 --> local_asset_path           本地的资产包路径 (str/unicode), z:/car
                 --> online_asset_path          资产库的资产包路径 (str/unicode), 如: /vehicle/car
                 --> call_back                  回调函数,用于计算进度, 默认为None
            返回: 成功返回True
            """
            global G_tw_http_ip
            global G_tw_token
            from twlib._asset_lib import _asset_lib
        
            if not isinstance(lib_sign, basestring) or not isinstance(local_asset_path, basestring) or not isinstance(online_asset_path, basestring):
                raise Exception("asset_lib.upload_asset argv error(str/unicode, str/unicode, str/unicode)")

            return _asset_lib.upload_asset(tw.send_web, G_tw_http_ip, G_tw_token, lib_sign, local_asset_path, online_asset_path, call_back)
        
        @staticmethod
        def download_asset(lib_sign, online_asset_path, local_asset_path, call_back=None):
            u"""
            描述: 下载资产包
            调用: download_asset(lib_sign, online_asset_path, local_asset_path, call_back=None)
                 --> lib_sign                   库标识 (str/unicode), 如lib_asset
                 --> online_asset_path        资产库的资产路径 (unicode/str), 如: /vehicle/car
                 --> local_asset_path         本地资产路径 (unicode/str)), 如:  z:/car
                 --> call_back                回调函数,用于计算进度, 默认为None
            返回: 成功返回True
            """
            global G_tw_http_ip
            global G_tw_token
            from twlib._asset_lib import _asset_lib
        
            if not isinstance(lib_sign, basestring) or not isinstance(local_asset_path, basestring) or not isinstance(online_asset_path, basestring):
                raise Exception("asset_lib.download_asset argv error(str/unicode, str/unicode, str/unicode)")

            return _asset_lib.download_asset(tw.send_web, G_tw_http_ip, G_tw_token, lib_sign, online_asset_path, local_asset_path, call_back)         
        
        @staticmethod
        def upload_file(lib_sign, local_path, online_asset_path, call_back=None, argv_dict={}):
            u"""
            描述: 上传文件到资产包
            调用: upload_file(lib_sign, local_path, online_asset_path, call_back=None, argv_dict={})
                 --> lib_sign                   库标识 (str/unicode), 如lib_asset
                 --> local_path                 本地文件丼或者目录路径 (str/unicode/list), 如: local_path为z:/1.txt 或者 z:/aa_dir 或者 [z:/1.txt, z:/aa_dir], 上传后对应资产库的路径为: /vehicle/car/1.txt,  vehicle/car/aa_dir
                 --> online_asset_path          资产库的资产包路径 (unicode/str), 如: /vehicle/car
                 --> call_back                  回调函数,用于计算进度, 默认为None
                 --> argv_dict                  其他参数(dict),目前支持key: online_child(str/unicode/list)为资产包下的路径,和local_path对应, 如本地上传路径为z:/aa/bb/1.txt, aa为资产包, online_child=/bb/1.txt
            返回: 成功返回True
            """
            global G_tw_http_ip
            global G_tw_token
            from twlib._asset_lib import _asset_lib
        
            if not isinstance(lib_sign, basestring) or not isinstance(local_path, (basestring, list)) or not isinstance(online_asset_path, basestring) or not isinstance(argv_dict,dict):
                raise Exception("asset_lib.upload_file argv error(str, str/unicode/list, str/unicode, dict)")

            return _asset_lib.upload_file(tw.send_web, G_tw_http_ip, G_tw_token, lib_sign, local_path, online_asset_path, call_back, argv_dict)
        
        @staticmethod
        def download_file(lib_sign, online_path, local_path, call_back=None):
            u"""
            描述: 下载文件
            调用: download_file(lib_sign, online_path, local_path, call_back=None)
                 --> lib_sign                   库标识 (str/unicode), 如lib_asset
                 --> online_path                资产库的文件路径 (unicode/str/list), 和local_path类型一致,都是str或者都是list
                 --> local_path                 本地文件路径 (str/unicode/list), 和online_path类型一致,都是str或者都是list
                 --> call_back                  回调函数,用于计算进度, 默认为None
            返回: 成功返回True
            """
            global G_tw_http_ip
            global G_tw_token
            from twlib._asset_lib import _asset_lib
        
            if not isinstance(lib_sign, basestring) or not isinstance(local_path, (basestring, list)) or not isinstance(online_path, (basestring, list)):
                raise Exception("asset_lib.download_file argv error(str/unicode/list, str/unicode/list)")

            return _asset_lib.download_file(tw.send_web, G_tw_http_ip, G_tw_token, lib_sign, online_path, local_path, call_back)
        
        @staticmethod
        def set_cover(lib_sign, online_asset_path, media_path):
            u"""
            描述: 设置封面
            调用: download_file(lib_sign, online_asset_path, media_path)
                 --> lib_sign                   库标识 (str/unicode), 如lib_asset
                 --> online_asset_path          资产库的资产包路径 (unicode/str), 如: /vehicle/car
                 --> media_path                 本地图片/视频路径 (str/unicode)
            返回: 成功返回True
            """
            global G_tw_http_ip
            global G_tw_token
            from twlib._asset_lib import _asset_lib
        
            if not isinstance(lib_sign, basestring) or not isinstance(online_asset_path, basestring) or not isinstance(media_path, basestring):
                raise Exception("asset_lib.set_cover argv error(str/unicode, str/unicode)")

            return _asset_lib.set_cover(tw.send_web, G_tw_http_ip, G_tw_token, lib_sign, online_asset_path, media_path)            
    
    class log:
        @staticmethod
        def fields():             
            u"""
            描述: 获取所有字段标识
            调用: fields()
            返回: 成功返回list
            """      
            return tw.send_web(tw.log.__name__, "fields", {})
        

        @staticmethod
        def get_id(db, filter_list, limit="5000"):
            u"""
            描述: 获取记录id列表
            调用: get_id(db, filter_list, limit="5000")
                 --> db                     数据库 (str/unicode)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
            返回: 成功返回list
            """                  
            if not isinstance(db, basestring) or not isinstance(filter_list, list) or not isinstance(limit, basestring):
                raise Exception("log.get_id argv error, there must be(str/unicode, list, str/unicode)")         
            return tw.send_web(tw.log.__name__, "get_id", {"db":db, "filter_array":filter_list, "limit":limit})
                    
        @staticmethod
        def get(db, id_list, field_list, limit="5000", order_list=[]):
            u"""
             描述:获取记录列表
             调用:get(db, id_list, field_list, limit="5000", order_list=[])
                  --> db               数据库 (str/unicode)
                  --> id_list          ID列表  (list)(最大长度20000)
                  --> field_list       字段列表 (list)
                  --> limit            限制条数 (str/unicode), 默认是5000
                  --> order_list       排序列表 (list),默认为空
             返回:成功返回list
             """               
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not isinstance(field_list, list) or \
               not isinstance(limit, basestring) or  not isinstance(order_list, list):
                raise Exception("log.get argv error, there must be (str/unicode, list, list, str/unicode, list)")    
            return tw.send_web(tw.log.__name__, "get", {"db":db, "field_array":field_list, "id_array":id_list, "order_field_array":order_list, "limit":limit})
        
        @staticmethod
        def get_filter(db, field_list, filter_list, limit="5000", order_list=[]):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, field_list, filter_list, limit="5000", order_list=[])
                 --> db                     数据库 (str/unicode)
                 --> field_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 --> limit                  限制条数 (str/unicode), 默认是5000
                 --> order_list        顺序的字段标识列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(db, basestring) or not isinstance(field_list, list) or not isinstance(filter_list, list)  or not isinstance(limit, basestring) or not isinstance(order_list, list) :
                raise Exception("log.get_filter argv error, there must be(list, list, str/unicode, list)")   
            
            return tw.send_web(tw.log.__name__, "get_filter", {"db":db, "field_array":field_list, "filter_array":filter_list, "order_field_array":order_list, "limit":limit})       
    
    class todo_group:  
        
        @staticmethod
        def fields():             
            u"""
            描述: 获取所有字段标识
            调用: fields()
            返回: 成功返回list
            """      
            return tw.send_web(tw.todo_group.__name__, "fields", {})
        
        @staticmethod
        def get_id(filter_list):
            u"""
             描述:获取记录id列表
             调用:get_id(filter_list)
                  --> filter_list             过滤语句列表 (list)
             返回: 成功返回list
             """   
            if not isinstance(filter_list, list):
                raise Exception("todo_group.get_id argv error, there must be(list)")  
            return tw.send_web(tw.todo_group.__name__, "get_id", {"filter_array":filter_list})
        
        @staticmethod
        def get(id_list, field_list, order_list=[]):
            u"""
             描述:获取记录列表
             调用:get(id_list, field_list, order_list=[])
                  --> id_list                 ID列表 (list)(最大长度20000)
                  --> field_list              字段列表 (list)
                  --> order_list              排序列表 (list)
             返回: 成功返回list
             """                
            if not isinstance(id_list, list) or not isinstance(field_list, list) or not isinstance(order_list, list):
                raise Exception("todo_group.get argv error, there must be(list, list, list)")              
            return tw.send_web(tw.todo_group.__name__, "get", {"field_array":field_list, "id_array":id_list, "order_field_array":order_list})
        
        @staticmethod
        def create(entity):
            u"""
             描述:创建记录
             调用:create(entity)
                  --> entity                  实体 (str/unicode)

             返回:成功返回ID
             """                
            if not isinstance(entity, basestring):
                raise Exception("todo_group.create argv error, there must be(str/unicode)")               
            return tw.send_web(tw.todo_group.__name__, "create", {"entity":entity})

        
        @staticmethod
        def set(id, entity):
            u"""
             描述:修改记录
             调用:set(id, entity)
                  --> id                      id (str/unicode)
                  --> entity                    实体 (str/unicode) 
             返回:成功返回True
             """                
            if not isinstance(entity, basestring) or not isinstance(id, basestring):
                raise Exception("todo_group.set argv error, there must be(str/unicode, str/unicode)")    
            return tw.send_web(tw.todo_group.__name__, "set", {"id":id, "entity":entity})
        
        @staticmethod
        def delete(id_list):
            u"""
            描述: 删除记录
            调用: delete(id_list)
                 --> id_list                 ID列表 (list)
            返回: 成功返回True
            """             
            if not isinstance(id_list, list):
                raise Exception("todo_group.delete argv error, there must be(list)")  
            return tw.send_web(tw.todo_group.__name__, "delete", {"id_array":id_list}) 
    
    class todo:  
        @staticmethod
        def fields():             
            u"""
            描述: 获取所有字段标识
            调用: fields()
            返回: 成功返回list
            """      
            return tw.send_web(tw.todo.__name__, "fields", {})     
        
        @staticmethod
        def get_id(filter_list):
            u"""
             描述:获取记录id列表
             调用:get_id(filter_list)
                  --> filter_list             过滤语句列表 (list)
             返回: 成功返回list
             """   
            if not isinstance(filter_list, list):
                raise Exception("todo.get_id argv error, there must be(list)")  
            return tw.send_web(tw.todo.__name__, "get_id", {"filter_array":filter_list})
        
        @staticmethod
        def get(id_list, field_list, order_list=[]):
            u"""
             描述:获取记录列表
             调用:get(id_list, field_list, order_list=[])
                  --> id_list                 ID列表 (list)(最大长度20000)
                  --> field_list              字段列表 (list)
                  --> order_list              排序列表 (list)
             返回: 成功返回list
             """                
            if not isinstance(id_list, list) or not isinstance(field_list, list) or not isinstance(order_list, list):
                raise Exception("todo.get argv error, there must be(list, list, list)")              
            return tw.send_web(tw.todo.__name__, "get", {"field_array":field_list, "id_array":id_list, "order_field_array":order_list})
        
        @staticmethod
        def create(todo_group_id, text, status="wait", start_date="", end_date="", head_account_id="", attend_account_id="", priority=""):
            u"""
             描述:创建记录
             调用:create(todo_group_id, text, status="wait", start_date="", end_date="", head_account_id="", attend_account_id="", priority="")
                  --> todo_group_id           分组ID (str/unicode)
                  --> text                    内容 (str/unicode)
                  --> status                  状态 (str/unicode), 状态在（wait, work, check, pause, finish, delay）
                  --> start_date              开始日期 (list), format: 2021-07-11
                  --> end_date                结束日期 (list), format: 2021-07-11
                  --> head_account_id         负责人账号ID(str/unicode)
                  --> attend_account_id       参与人账号ID(str/unicode), 多人以逗号隔开
                  --> priority                优先级(str/unicode), P1到P4
             返回:成功返回ID
             """                

            if not isinstance(todo_group_id, basestring) or not isinstance(text, basestring) or not isinstance(status, basestring) or \
               not isinstance(start_date, basestring) or not isinstance(end_date, basestring) or \
               not isinstance(head_account_id, basestring) or not isinstance(attend_account_id, basestring)  or not isinstance(priority, basestring) :
                raise Exception("todo.create argv error, there must be(str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode, str/unicode)")               
            return tw.send_web(tw.todo.__name__, "create", {
                "todo_group_id":todo_group_id,
                "text":text,
                "status":status,
                "start_date":start_date,
                "end_date":end_date,
                "head_account_id":head_account_id,
                "attend_account_id":attend_account_id,
                "priority":priority,            
                })

        
        @staticmethod
        def set(id, data_dict):        
            u"""
            描述:更新单条记录
            调用:set(id, data_dict)
                 --> id                ID (str/unicode)
                 --> data_dict         更新的数据 (dict)
            返回:成功返回True
            """             
            if not isinstance(id, basestring) or not isinstance(data_dict, dict):
                raise Exception("todo.set argv error, there must be (str/unicode, dict)")                 
            return tw.send_web(tw.todo.__name__, "set", {"id":id, "field_data_array":data_dict})
        
        @staticmethod
        def delete(id_list):
            u"""
            描述: 删除记录
            调用: delete(id_list)
                 --> id_list                 ID列表 (list)
            返回: 成功返回True
            """             
            if not isinstance(id_list, list):
                raise Exception("todo.delete argv error, there must be(list)")  
            return tw.send_web(tw.todo.__name__, "delete", {"id_array":id_list})        
    
    class pipeline_template:
        @staticmethod
        def fields():
            u"""
             描述:获取所有字段标识
             调用:fields()
             返回:成功返回list
             """               
            return tw.send_web(tw.pipeline_template.__name__, "fields", {})
        
        @staticmethod
        def get(db, module, field_list, filter_list=[]):
            u"""获取阶段模版记录列表

            参数:
                - `db` (str): 数据库
                - `module` (str): 模块
                - `field_list` (list): 字段列表
                - `filter_list` (list, 可选): 过滤条件列表. 默认为: [].

            返回:

                list: [{..}]
            """
            if not isinstance(db, basestring) or not isinstance(module, basestring) or not isinstance(field_list, list) or not isinstance(filter_list, list):
                raise Exception("pipeline_template.get argv error ,there must be (str/unicode, str/unicode, list, list)")             
            return tw.send_web(tw.pipeline_template.__name__, "get", {"db":db, "module":module, "field_array":field_list,'filter_array':filter_list})

    class relate:
        @staticmethod
        def get(db, id_list):
            u"""
            描述: 获取关联记录
            调用: get(db, id_list)
                  --> db                      数据库(str/unicode)
                  --> id_list                 ID列表 (list)
            返回: 成功返回[]
            """ 
            if not isinstance(db, basestring) or not isinstance(id_list, list):
                raise Exception("relate.get argv error, there must be (str/unicode, list)")
            return tw.send_web(tw.relate.__name__, "get", {"db":db, "id_array":id_list})
    
        @staticmethod
        def link(db, id_list, link_id_list):
            u"""
            描述: 关联记录
            调用: link(db, id_list, link_id_list)
                  --> db                      数据库(str/unicode)
                  --> id_list                 ID列表 (list)
                  --> link_id_list            关联ID列表 (list)
            返回: 成功返回True
            """ 
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not isinstance(link_id_list, list):
                raise Exception("relate.link get argv error, there must be (str/unicode, list, list)")
            return tw.send_web(tw.relate.__name__, "link", {"db":db, "id_array":id_list, "link_id_array":link_id_list})            

        @staticmethod
        def unlink(db, id_list, link_id_list):
            u"""
            描述: 取消关联记录
            调用: link(db, id_list, link_id_list)
                  --> db                      数据库(str/unicode)
                  --> id_list                 ID列表 (list)
                  --> link_id_list            关联ID列表 (list)
            返回: 成功返回True
            """ 
            if not isinstance(db, basestring) or not isinstance(id_list, list) or not isinstance(link_id_list, list):
                raise Exception("relate.unlink get argv error, there must be (str/unicode, list, list)")
            return tw.send_web(tw.relate.__name__, "unlink", {"db":db, "id_array":id_list, "link_id_array":link_id_list})   

    class department:
        
        @staticmethod
        def fields():
            u"""
             描述:获取所有字段标识
             调用:fields()
             返回:成功返回list
             """   
            return tw.send_web(tw.department.__name__, "fields", {})

        @staticmethod
        def get_id(filter_list):
            u"""
             描述:获取记录id列表
             调用:get_id(filter_list)
                  --> filter_list           过滤语句列表 (list)
             返回:成功返回list
             """              
            if not isinstance(filter_list, list):
                raise Exception("department.get_id argv error ,there must be (list)")          
            return tw.send_web(tw.department.__name__, "get_id", {"filter_array":filter_list})
                    
        @staticmethod
        def get(id_list, field_list):
            u"""
             描述:获取记录列表
             调用:get(id_list, field_list)
                  --> db                   数据库 (str/unicode)
                  --> id_list              ID列表 (list)(最大长度20000)
                  --> field_list           字段列表 (list)
             返回:成功返回list
             """             
            if not isinstance(id_list, list) or not  isinstance(field_list, list):
                raise Exception("department.get argv error ,there must be (list, list)")          
            return tw.send_web(tw.department.__name__, "get", {"field_array":field_list, "id_array":id_list})
        
        @staticmethod
        def get_filter(field_list, filter_list):
            u"""
            描述: 获取记录列表
            调用: get_filter(db, field_list, filter_list)
                 --> db                     数据库 (str/unicode)
                 --> field_list        字段标识列表 (list)
                 --> filter_list            过滤语句列表 (list)
                 
            返回: 成功返回list
            """              
            if not isinstance(field_list, list) or not isinstance(filter_list, list):
                raise Exception("department.get_filter argv error, there must be(list, list)")   
            
            return tw.send_web(tw.department.__name__, "get_filter", {"field_array":field_list, "filter_array":filter_list})
        

if __name__ == "__main__":
    t_tw = tw("192.168.199.48:8383", "admin", "shiming123")
    #pass
    # t_tw = tw()
    # print(t_tw.get_version())

    #---------------com-----------------
    # print((t_tw.com.get_server_time()))
    # print((t_tw.com.get_os()))
    
    #---------------client-----------------
    # print(t_tw.client.get_argv_key('sys'))
    # print(t_tw.client.get_sys_key('id_list'))
    # print(t_tw.client.get_database())
    # print(t_tw.client.get_id())
    # print(t_tw.send_web("c_work_flow","get_python_qc_data", {"db":'proj_xiaoying', "module":"shot", "module_type":"task",  "task_id":'192F00E6-DD14-6F6D-C356-3D2EA72CA754'})[0])

    # print(t_tw.send_local_http("", "", "screening_full", {"sign":"screen_widget", "method":"fullscreen"}))
    # print(t_tw.client.open_qc_widget('proj_xiaoying', 'shot', '192F00E6-DD14-6F6D-C356-3D2EA72CA754',{'flow_id': '1D68EA67-7DCE-4DE1-4CC8-8FA86F76C8F6', 'field_id': '81FCC7D3-AF38-98BA-36D9-2A66B669B144', 'field_sign': 'task.leader_status', 'field_str': '内部审核', 'en_name': 'Leader_review', 'status_id': '1C82E03F-574D-43EC-A07B-89B948C68D5E', 'status': 'Approve', 'status_type': 'approve', 'color': '#00AC56', 'submit_type': 'review'}))
    # print(t_tw.client.refresh_all('proj_xiaoying','shot','task'))

    #系统执行插件的读取的
    
    #---------------login-----------------
    #print((t_tw.login.account()))
    # print((t_tw.login.account_id()))
    # print((t_tw.login.token()))
    #print((t_tw.login.http_server_ip()))
    #print((t_tw.login.is_login()))
    
    
    #---------------status-----------------
    #print(tw.status.get_status_and_color())
    
    #---------------account-----------------
    # print(t_tw.account.fields())
    #print(t_tw.account.fields_and_str())
    #t_id_list=t_tw.account.get_id([])
    #print(t_id_list)
    #print(t_tw.account.get(t_id_list,  ["account.id","account.entity"]))
    #print(t_tw.account.set([t_id_list[0]],  {"account.mail":"ddd"}))
    #print(t_tw.account.count([]))
    #print(t_tw.account.distinct([], "account.entity", ["account.entity"]))
    #print(t_tw.account.group_count(["account.entity"], []))
    #print(t_tw.account.get_filter(["account.id", "account.entity"], [["account.status", "=", "Y"]], limit="2", order_sign_list=["account.entity"], start_num=""))
    
    #---------------project-----------------
    #print(t_tw.project.fields())
    #print(t_tw.project.fields_and_str())
    #t_id_list=t_tw.project.get_id([])
    #print(t_id_list)
    #print(t_tw.project.get(t_id_list,  ["project.id","project.entity"]))
    #print(t_tw.project.set([t_id_list[0]],  {"project.description":"ddd"}))
    #print(t_tw.project.count([]))
    #print(t_tw.project.distinct([], "project.entity", ["project.entity"]))
    #print(t_tw.project.group_count(["project.entity"], [])) 
    #print(t_tw.project.get_filter(["project.id", "project.entity"], [["project.status", "!~", "Close"]], limit="2", order_sign_list=["project.entity"], start_num=""))
    
    
    #---------------info-----------------
    #print(t_tw.info.modules("proj_big"))
    #print(t_tw.info.fields("proj_big", "shot"))
    #print(t_tw.info.fields_and_str("proj_big", "shot"))    
    #t_id_list=t_tw.info.get_id("proj_big", "shot", [ ])
    #print(t_id_list)
    #print(t_tw.info.get("proj_big", "shot", t_id_list,  ["shot.id","eps.entity", "shot.entity"]))
    #print(t_tw.info.get_dir("proj_big", "shot", t_id_list,  ["lay_check"]))
    #print(t_tw.info.get_field_and_dir("proj_big", "shot",  t_id_list,  ["eps.entity", "shot.entity"], ["lay_check"]))
    #print(t_tw.info.get_makedirs("proj_big", "shot", t_id_list))
    #print(t_tw.info.get_sign_filebox("proj_big", "shot", t_id_list[0], "lay"))
    #print(t_tw.info.get_filebox("proj_big", "shot", t_id_list[0], "E4ACF507-6861-2E2E-273C-5610B118B9EF"))
    #print(t_tw.info.set("proj_big", "shot",  [t_id_list[0]],  {"shot.frame":"66"}))
    #print(t_tw.info.delete("proj_big", "shot", t_id_list))
    #print(t_tw.info.create("proj_big", "shot", {"shot.entity":"sk1", "eps.id":"19057284-1DCD-F852-BAEA-9988553004DE"}))
    #print(t_tw.info.create("proj_big", "shot", {"shot.entity":"sk2", "eps.entity":"EP01"}))
    #print(t_tw.info.create("proj_big", "shot", {"shot.entity":"sk3", "shot.link_eps":"19057284-1DCD-F852-BAEA-9988553004DE"}))
    #print(t_tw.info.download_image("proj_big", "shot", t_id_list, "shot.image")) 
    #print(t_tw.info.set_image("proj_big", "shot", t_id_list, "shot.image", "Z:/test_image/22.jpg")) 
    #print(t_tw.info.count("proj_big", "shot", [  ]))
    #print(t_tw.info.distinct("proj_big", "shot", [], "eps.entity", ["eps.entity"]))
    #print(t_tw.info.group_count("proj_big", "shot", ["eps.entity"], [  ]))
    #print(t_tw.info.send_msg("proj_big", "shot", t_id_list[0], ["A98C9570-F63D-84A5-1620-3EA8CB13D87E"], "test")) 
    #print(t_tw.info.download_media("proj_big", "shot", t_id_list, "shot.image")) 
    #print(t_tw.info.set_media("proj_big", "shot", t_id_list, "shot.image", ["Z:/test_image/33.jpg"]))     
    #print(t_tw.info.get_filter("proj_big", "shot", ["shot.id", "shot.entity"], [], limit="10", order_sign_list=["shot.entity"], start_num=""))
    # print(t_tw.info.publish("proj_sm", "shot", "0C517667-28FD-EFC2-0CE8-9F64DBE5BE82", ["z:/1.gif"], "lay"))

    
    #---------------task-----------------
    #print(t_tw.task.modules("proj_big"))
    #print(t_tw.task.fields("proj_big", "shot"))
    #print(t_tw.task.fields_and_str("proj_big", "shot"))      
    #t_id_list=t_tw.task.get_id("proj_big", "shot", [ ["eps.entity", "=", "EP01"],["shot.entity", "=", "EP01_shot003"],["task.entity", "=", "Layout"]])
    #print(t_id_list)
    #print(t_tw.task.get("proj_big", "shot", t_id_list,  ["eps.entity", "shot.entity"]))
    #print(t_tw.task.get_dir("proj_big", "shot", t_id_list,  ["lay_check"]))
    #print(t_tw.task.get_field_and_dir("proj_big", "shot",  t_id_list,  ["eps.entity", "shot.entity"], ["lay_check"]))
    #print(t_tw.task.get_makedirs("proj_big", "shot", t_id_list))
    #print(t_tw.task.get_submit_filebox_sign("proj_big", "shot", t_id_list[0]))
    #print(t_tw.task.get_sign_filebox("proj_big", "shot", t_id_list[0], "review"))
    #print(t_tw.task.get_filebox("proj_big", "shot", t_id_list[0], "67B9A8CF-9DAE-8E05-342E-9E44C69976C2"))
    #print(t_tw.task.get_review_file("proj_big", "shot", ["AB612671-54FB-A049-CE84-788A10E73532"]))
    #print(t_tw.task.get_version_file("proj_big", "shot", ["AB612671-54FB-A049-CE84-788A10E73532"], "review"))
    #print(t_tw.task.set("proj_big", "shot",  t_id_list,  {"task.start_date":"2018-02-02"}))
    #print(t_tw.task.delete("proj_big", "shot", t_id_list))
    #t_shot_id="8764D1E4-764D-726E-5152-8EE2CD143F1A"
    #t_pipeline_id="3429200E-6801-4FD8-A742-8F2767674FB2"
    #t_flow_id="1110c3da-3444-4f37-a7fa-04846da3c879"
    #print(t_tw.task.create("proj_big", "shot", t_shot_id, t_pipeline_id, "Layout2", t_flow_id, pipeline_template_id="7EC21E8C-C6A5-EF1F-719F-C0A58BD3403F"))
    #print(t_tw.task.set_image("proj_big", "shot", t_id_list, "task.image", "Z:/test_image/22.jpg")) 
    #print(t_tw.task.download_image("proj_big", "shot", t_id_list, "task.image", is_small=False))  
    
    #print(t_tw.task.count("proj_big", "shot", [ ]))
    #print(t_tw.task.distinct("proj_big", "shot", [], "eps.entity", ["eps.entity"]))
    #print(t_tw.task.assign("proj_big", "shot", t_id_list, "A98C9570-F63D-84A5-1620-3EA8CB13D87E"))
    #print(t_tw.task.submit("proj_big", "shot", t_id_list[0],["F:/test_004.gif"], "submit png", "review")) 
    #print(t_tw.task.update_flow("proj_big", "shot", t_id_list[0], "task.leader_status","Approve", "note data", ["z:/1.gif"])) 
    #print(t_tw.task.group_count("proj_big", "shot", ["task.pipeline"], [ ["task.status", "=", "Approve" ] ]))
    #print(t_tw.task.send_msg("proj_big", "shot", t_id_list[0], ["A98C9570-F63D-84A5-1620-3EA8CB13D87E"], "test2")) 
    #print(t_tw.task.publish("proj_big", "shot", t_id_list[0], ["F:/test_006.gif"], "review", "006")) 
    #print(t_tw.task.set_media("proj_big", "shot", t_id_list, "task.image", ["Z:/test_image/33.jpg"]))        
    #print(t_tw.task.download_media("proj_big", "shot", t_id_list, "task.image")) 
    #print(t_tw.task.get_filter("proj_big", "shot", ["task.id", "task.entity"], [], limit="10", order_sign_list=["task.entity"], start_num=""))
    
    
    #---------------etask-----------------
    #print(t_tw.etask.fields("proj_task"))
    #print(t_tw.etask.fields_and_str("proj_task"))      
    #t_id_list=t_tw.etask.get_id("proj_task", [ ["type.entity", "=", "shot"],["etask.url", "has", "ep01/seq01/shot01"]])    
    #t_id_list=t_tw.etask.get_id("proj_task", [ ["type.entity", "=", "task"],["etask.url", "has", "ep01/seq01/shot02"]])    
    #print(t_id_list)
    #print(t_tw.etask.get("proj_task", t_id_list,  ["etask.entity"]))
    #print(t_tw.etask.get_dir("proj_task", t_id_list,  ["work", "check"]))
    #print(t_tw.etask.get_field_and_dir("proj_task", t_id_list,  ["etask.entity"], ["work", "check"]))
    #print(t_tw.etask.get_makedirs("proj_task", t_id_list))
    #print(t_tw.etask.get_submit_filebox_sign("proj_task", t_id_list[0]))
    #print(t_tw.etask.get_sign_filebox("proj_task", t_id_list[0], "review"))
    #print(t_tw.etask.get_filebox("proj_task", t_id_list[0], "9B642482-EBC4-4C58-A101-D97EFA125E35"))
    #print(t_tw.etask.get_review_file("proj_task", t_id_list))
    #print(t_tw.etask.get_version_file("proj_task", t_id_list, "review"))
    #print(t_tw.etask.set("proj_task", t_id_list,  {"etask.start_date":"2021-08-02"}))
    #print(t_tw.etask.delete("proj_task", t_id_list))
    #print(t_tw.etask.create("proj_task", "shot", {"etask.link_id":"9C18846B-CCF5-A1E8-09EA-CECD612A17BB", "etask.entity":"shot02"}))
    
    #t_link_id="A41E85DA-301B-9877-B278-1C77AAB388A2"
    #t_pipeline_id="71AF8214-1DFF-86A7-A6D1-BD05FD521122"
    #t_flow_id="ECB3C031-CC9B-6088-2ED7-9A313DDE3FD8"
    #print(t_tw.etask.create_task("proj_task", t_link_id, t_pipeline_id, "Layout", t_flow_id))
    #print(t_tw.etask.set_image("proj_task", t_id_list, "etask.image", "Z:/test_image/22.jpg")) 
    #print(t_tw.etask.download_image("proj_task", t_id_list, "etask.image", is_small=False))  
    
    #print(t_tw.etask.count("proj_task", [ ["type.entity", "=", "shot"] ]))
    #print(t_tw.etask.distinct("proj_task", [ ["type.entity", "=", "shot"] ], "etask.entity", ["etask.entity"]))
    #print(t_tw.etask.assign("proj_task", t_id_list, "A98C9570-F63D-84A5-1620-3EA8CB13D87E", "2021-08-02", "2021-08-22"))
    #print(t_tw.etask.submit("proj_task", t_id_list[0],["Z:/shot02_v003.mp4"], "submit png", "review")) 
    #print(t_tw.etask.update_flow("proj_task", t_id_list[0], "etask.leader_status","Approve", "note data", [ "Z:/test_image/4.png" ])) 
    #print(t_tw.etask.group_count("proj_task", ["pipeline.entity"], [ ["type.entity", "=", "task"], ["etask.status", "=", "Wait" ] ]))
    #print(t_tw.etask.send_msg("proj_task", t_id_list[0], ["A98C9570-F63D-84A5-1620-3EA8CB13D87E"], "test23333")) 
    #print(t_tw.etask.set_media("proj_task", t_id_list, "etask.image", ["Z:/test_image/5.png"]))        
    #print(t_tw.etask.download_media("proj_task", t_id_list, "etask.image"))     
    #print(t_tw.etask.publish("proj_task", t_id_list[0], ["Z:/shot02_v004.mp4"], "review", "004")) 
    #print(t_tw.etask.get_filter("proj_task", ["etask.id", "etask.entity"], [], limit="10", order_sign_list=["etask.entity"], start_num=""))
    
    
    #---------------note-----------------
    #print(t_tw.note.fields("proj_big"))
    #t_id_list=t_tw.note.get_id("proj_big", [ ["module","=", "shot"], ["module_type","=", "task"] ])
    #print(t_id_list)
    #print(t_tw.note.get("proj_big", t_id_list, ["#id", "dom_text"]))
    #print(t_tw.note.create("proj_big", "shot", "task", ["5DD4237B-8B86-E409-9C96-D76E52FE895A"], "test note", "",["z:/1.gif"], tag_list=["ska", "3",u'中午'])) 
    #print(t_tw.note.set("proj_big", "EF47C7D7-06F4-3C83-BFF3-E3CA90462CE2", [{"type":"text", "content":"test notedd"}, {"type":"image", "path":"Z:/1.gif"}], tag_list=["aa", "cc", "1"]))
    #print(t_tw.note.get_filter("proj_big", ["dom_text"], [], limit="10", order_list=["time"]))
    
    #--------------filebox---------------
    #print(t_tw.filebox.fields())
    #t_id_list=t_tw.pipeline.get_id("proj_big", [ ["module", "=", "shot"], ["module_type","=", "task"] ])
    #print(t_tw.filebox.get("proj_big", "shot", "task", t_tw.filebox.fields(), t_id_list))
    
    #--------------field---------------
    #print(t_tw.field.type())
    #print(t_tw.field.create("proj_big", "shot", "info", "测数据", "test_data_c", "test_data_c", "int"))
    
    
    #---------------plugin------------------
    #print(t_tw.plugin.fields())
    #t_id_list=t_tw.plugin.get_id([ ["type","=","menu"]])
    #print(t_id_list)
    #print(t_tw.plugin.get([t_id_list[0]], ["name", "argv"]))
    #print(t_tw.plugin.get_argvs(t_id_list[0]))
    #print(t_tw.plugin.set_argvs(t_id_list[0], {'action': 'rv_palyer_filebox_sign', 'type': 'series', 'filebox_sign': '', 'rv_path': ''}))
    
    
    #---------------pipeline------------------
    #print(t_tw.pipeline.fields())
    #t_id_list=t_tw.pipeline.get_id("proj_big", [ ["module", "=", "shot"], ["module_type","=", "task"] ])
    #print(t_id_list)
    #print(t_tw.pipeline.get("proj_big", t_id_list, t_tw.pipeline.fields()))
    #print(t_tw.pipeline.get_filter("proj_big", t_tw.pipeline.fields(), [ ["module", "=", "shot"], ["module_type","=", "task"] ]))
    
    
    #---------------history------------------
    #print(t_tw.history.fields("proj_big"))
    #t_id_list=t_tw.history.get_id("proj_big", [ ["module","=", "shot"], ["module_type", "=", "task"] ])
    #print(t_id_list)
    #print(t_tw.history.get("proj_big", t_id_list, ["status", "text", "#link_id", "module", "module_type"]))
    #print(t_tw.history.count("proj_big", [ ["module","=", "shot"], ["module_type", "=", "task"] ]))
    #print(t_tw.history.get_filter("proj_big", ["status", "text", "#link_id", "module", "module_type", "time"], [ ["module","=", "shot"], ["module_type", "=", "task"] ], limit="10", order_list=["time"]))
    
    #---------------link------------------
    #t_link_id_list=t_tw.info.get_id("proj_big", "asset", [["asset.entity", "has", "%"]])
    #t_id_list=t_tw.task.get_id("proj_big", "shot", [ ["shot.entity", "has", "EP01_shot001"]]) 
    #print(t_link_id_list, t_id_list)
    #print(t_tw.link.get_asset("proj_big", "shot", "task", t_id_list[0]))
    #print(t_tw.link.link_asset("proj_big", "shot", "task", t_id_list, t_link_id_list))
    #print(t_tw.link.get_entity("proj_big", "shot", "task", t_id_list[0], "asset"))
    #print(t_tw.link.link_entity("proj_big", "shot", "task", t_id_list, "asset", t_link_id_list))
    #print(t_tw.link.unlink_entity("proj_big", "shot", "task", t_id_list, "asset", [t_link_id_list[0]]))
    
    #t_link_id_dict={}
    #for i in t_link_id_list:
        #t_link_id_dict[i]=2#个数
    #print(t_tw.link.link_asset_num("proj_big", "shot", "task", t_id_list, t_link_id_dict))
    #print(t_tw.link.unlink_asset("proj_big", "shot", "task", t_id_list, t_link_id_list))
    #print(t_tw.link.reset_link_asset_num('proj_big','shot','task',t_id_list,t_link_id_dict))
    # print(t_tw.link.reset_link_entity_num('proj_sm','shot','task',["FF81B7BF-5D9A-140D-698C-30BD5E98B302"],"asset", {"301E5BD2-6941-7353-D5E4-7BC34185C2C9":8}))
    
    #---------------software------------------
    #print(t_tw.software.types())
    #print(t_tw.software.get_path("proj_big", "Nuke"))
    #print(t_tw.software.get_with_type("proj_big", "nuke"))
    
    
    #---------------api_data------------------
    #print(t_tw.api_data.set("proj_big", "test", "data", False))
    #print(t_tw.api_data.get("proj_big", "test",  False))
    
    
    #---------------version------------------
    #print(t_tw.version.fields("proj_big"))
    #t_id_list=t_tw.version.get_id("proj_big", [])
    #print(t_id_list)
    #print(t_tw.version.get("proj_big", t_id_list, ["#id", "entity", "status", "sign"]))
    #print(t_tw.version.create("proj_big", "9E6DFFFA-558E-7FAC-EF67-488E636C4E4C", "review",{"ddd":"dd3"}))
    #print(t_tw.version.get_filter("proj_big", ["#id", "entity", "status", "sign"], [ ["module","=", "shot"], ["module_type", "=", "task"] ], limit="10", order_list=["#link_id", "entity"]))
    
    #---------------link_entity------------------
    #print(t_tw.link_entity.get_name("proj_big", "shot", "task","9E6DFFFA-558E-7FAC-EF67-488E636C4E4C"))
    #print(t_tw.link_entity.get("proj_big", "shot", "task", "EP01"))
    
    
    #---------------timelog------------------
    #print(t_tw.timelog.fields())
    #t_id_list=t_tw.timelog.get_id("proj_big", [ ["module", "=", "shot"], ["module_type", "=", "task"] ])
    #print(t_id_list)
    #print(t_tw.timelog.get("proj_big", t_id_list, ["#id", "use_time", "date", "create_by"], "5000",["date"]))
    #print(t_tw.timelog.create("proj_big", "9E6DFFFA-558E-7FAC-EF67-488E636C4E4C", "shot", "task", "01:0a", "2018-06-20", "test sss"))
    #print(t_tw.timelog.set("proj_big", t_id_list[0], {"text": "test again data2"}))
    
    
    #-------------------flow---------------------
    #t_pipeline_id_list=t_tw.pipeline.get_id("proj_big", [ ["module", "=", "shot"], ["module_type","=", "task"] ])
    #print(t_tw.flow.get_data("proj_big", t_pipeline_id_list))        
    
    
    #------------------media_file---------------
    # t_id_list=t_tw.task.get_id("proj_xiaoying", "shot", [ ])
    # t_filebox_dict=t_tw.task.get_sign_filebox("proj_xiaoying", "shot", t_id_list[0], "review") 
    # print(t_id_list)
    # print(t_filebox_dict)
    # t_filebox_id=t_filebox_dict["#id"]
    # print(t_filebox_id)
    
    
    #print(t_tw.media_file.upload('proj_big',['z:/1.swf'],['/1.swf'])) 
    #print(t_tw.media_file.download('proj_big',['/1.swf'],['f:/1.swf'])) 
    #t_filebox_id = t_tw.task.get_sign_filebox('proj_big', 'shot', '5DD4237B-8B86-E409-9C96-D76E52FE895A', 'approve')['#id']
    #print(t_tw.media_file.upload_filebox('proj_big','shot', 'task', '5DD4237B-8B86-E409-9C96-D76E52FE895A', t_filebox_id, [u'z:/3.gif']))     
    #print(t_tw.media_file.download_filebox('proj_big','shot', 'task', '5DD4237B-8B86-E409-9C96-D76E52FE895A', t_filebox_id))     
    #print(t_tw.media_file.delete('proj_big',[u'/1.swf'])) 
    #print(t_tw.media_file.download_lastest('proj_big','/Big/Shot/Layout/EP01/EP01_shot001/approve','f:/','2017-01-01')) 
    
    #------------------server---------------
    #print(t_tw.server.fields())
    #print(t_tw.server.get("proj_big", ['name', 'win_path', 'mac_path', 'linux_path','#id']))
    #print(t_tw.server.get_path("proj_big", 'EBEF14A7-9E6E-1464-C2E3-D2F9CD7C2B46', "win"))
    
    #------------------file---------------
    #print(t_tw.file.fields("proj_big"))
    #t_task_id_list=t_tw.task.get_id("proj_big", "shot", [])
    #verison_id= t_tw.version.create("proj_big", t_task_id_list[0], "review",{"ddd":"23dd"})    
    #print(t_tw.file.create("proj_big", "shot", "task", t_task_id_list[0], verison_id, u"x:/1.gif", False,{"ssss":"ccc"}))
    #t_id_list=t_tw.file.get_id("proj_big", [ ])
    #print(t_id_list)    
    #print(t_tw.file.get("proj_big", ["3220A52A-4426-0D7F-2BA8-D962E45C2B0B"], ["#server_id", "sys_local_path", "sys_local_full_path", "#version_id"]))
    #print(t_tw.file.delete("proj_big", ["3220A52A-4426-0D7F-2BA8-D962E45C2B0B"]))
    #print(t_tw.file.get_filter("proj_big", ["#server_id", "sys_local_path", "sys_local_full_path", "#version_id"], [ ], limit="10", order_list=["#link_id"]))
    
    
    #------------------msg_queue---------------
    #print(t_tw.msg_queue.create("render_pool", {"db":"proj_big", "module":"shot", "module_type":"task"}))
    # print(t_tw.msg_queue.get("render_pool"))
    #------------------asset_lib---------------
    #print(t_tw.asset_lib.upload_asset("lib_mod", u'z:/tif', '/tif')) 
    #print(t_tw.asset_lib.download_asset("lib_mod", u'/tif', u'f:/tif')) 
    #print(t_tw.asset_lib.upload_file("lib_mod", [u'Z:/tif', u"z:/2.gif"], '/aa/tif')) 
    #print(t_tw.asset_lib.download_file("lib_mod", ['/aa/tif/2.gif'], ['f:/world/2.gif'])) 
    #print(t_tw.asset_lib.download_file("lib_mod", '/aa/tif/2.gif', 'f:/world/2.gif'))    
    
    #------------------log---------------
    #t_field_list=t_tw.log.fields()
    #t_id_list = t_tw.log.get_id("proj_big", [ ])
    #print(t_tw.log.get("proj_big", t_id_list, t_field_list, limit="200", order_list=["time"]))     
    #print(t_tw.log.get_filter("proj_big",  t_field_list, [ ], limit="200", order_list=["time"]))     
    
    #------------------todo_group---------------
    #t_field_list=t_tw.todo_group.fields()
    #print(t_field_list)
    #t_id_list = t_tw.todo_group.get_id([])
    #print(t_tw.todo_group.get(t_id_list, t_field_list))  
    #print(t_tw.todo_group.create("req"))
    #print(t_tw.todo_group.set("1CB2965F-1992-82CF-5210-C19B418EF17D", "rek"))
    #print(t_tw.todo_group.delete(["1CB2965F-1992-82CF-5210-C19B418EF17D"]))
    
    #------------------todo---------------
    #t_field_list=t_tw.todo.fields()
    #print(t_field_list)
    #t_id_list = t_tw.todo.get_id([])
    #print(t_id_list)
    #print(t_tw.todo.get(t_id_list, t_field_list))
    #print(t_tw.todo.create("4DB7748E-5357-B30B-7B75-464C6C925EFF", "AK47", "wait", "2021-01-02", "2021-10-02", "A98C9570-F63D-84A5-1620-3EA8CB13D87E", "A98C9570-F63D-84A5-1620-3EA8CB13D87E,B243ECC9-B3E3-2625-783E-D99740691FD6", "P3"))
    #print(t_tw.todo.set("819F5960-24F6-6330-D84F-3411EF02161E", {"text":"xxx"}))       
    #print(t_tw.todo.delete(["819F5960-24F6-6330-D84F-3411EF02161E"]))
    
    #--------------pipeline_template---------------
    #print t_tw.pipeline_template.fields()
    #print t_tw.pipeline_template.get("proj_big", "shot", ["entity"])     
    
    #--------------etask_type---------------
    #print(t_tw.etask_type.fields())
    #t_id_list=t_tw.etask_type.get_id("proj_sm_etask", [])
    #print(t_id_list)
    #print(t_tw.etask_type.get("proj_sm_etask", t_id_list, ["entity", "sign"]))
    #print(t_tw.etask_type.get_filter("proj_sm_etask", ["entity", "sign"], []))    

    #--------------department---------------
    # print(t_tw.department.fields())
    # t_id_list=t_tw.department.get_id([])
    # print(t_id_list)
    # print(t_tw.department.get(t_id_list, t_tw.department.fields()))
    # print(t_tw.department.get_filter(t_tw.department.fields(), []))

    #--------------relate---------------
    # print(t_tw.relate.get("proj_sm", ["D0FC61A2-0A5F-8E24-8922-5178142E2B52", "06549BDD-2182-72B9-55EF-8BE9A7B69C8E"]))
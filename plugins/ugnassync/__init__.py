import datetime
from threading import Event
from typing import Tuple, List, Dict, Any
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.utils.http import RequestUtils
from app.core.event import eventmanager, Event
from app.schemas.types import EventType


class DoubanRank(_PluginBase):
    # 插件名称
    plugin_name = "刷新绿联媒体库"
    # 插件描述
    plugin_desc = "刷新绿联媒体库"
    # 插件图标
    plugin_icon = "movie.jpg"
    # 插件版本
    plugin_version = "1.0.0"
    # 插件作者
    plugin_author = "ylme"
    # 作者主页
    author_url = "https://github.com/flyble"
    # 插件配置项ID前缀
    plugin_config_prefix = "ugnas_"
    # 加载顺序
    plugin_order = 101
    # 可使用的用户级别
    auth_level = 1

    # 退出事件
    _event = Event()
    # 私有属性
    _scheduler = None
    _api_token = ""
    _enabled = False
    _onlyonce = False
    _ugnasurl = ""

    def init_plugin(self, config: dict = None):
         # 停止现有任务
        self.stop_service()

        if config:
            self._enabled = config.get("enabled")
            self._onlyonce = config.get("onlyonce")
            self._api_token = config.get("api_token")
            self._token = config.get("ugnasurl")
    
       

        # 启动服务
        if self._enabled or self._onlyonce:
            if self._onlyonce:
                self._scheduler = BackgroundScheduler(timezone=settings.TZ)
                logger.info("绿联刷新媒体库服务启动，立即运行一次")
                self._scheduler.add_job(func=self.__request_csf, trigger='date',
                                        run_date=datetime.datetime.now(
                                            tz=pytz.timezone(settings.TZ)) + datetime.timedelta(seconds=3)
                                        ,name="刷新绿联媒体库")

                # 关闭一次性开关
                self._onlyonce = False
        # 保存配置
        self.update_config({
            "enabled": self._enabled,
            "onlyonce": False,
            "api_token": self._api_token,
            "ugnasurl": self._token
        })

            # 启动任务
        if self._scheduler.get_jobs():
            self._scheduler.print_jobs()
            self._scheduler.start()

    def get_state(self) -> bool:
        return self._enabled
    
    def get_service(self) -> List[Dict[str, Any]]:
        """
        注册插件公共服务
        [{
            "id": "服务ID",
            "name": "服务名称",
            "trigger": "触发器：cron/interval/date/CronTrigger.from_crontab()",
            "func": self.xxx,
            "kwargs": {} # 定时器参数
        }]
        """
        pass
    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'onlyonce',
                                            'label': '立即检测一次',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'ugnasurl',
                                            'label': '地址',
                                            'placeholder': 'http://192.158.1.1'
                                        }
                                    }
                                ]
                            },
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'api_token',
                                            'label': 'api_token',
                                            'placeholder': ''
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VAlert',
                                        'props': {
                                            'type': 'info',
                                            'variant': 'tonal',
                                            'text': '抓包token和url'
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                    
                ]
            }
        ], {
            "enabled": False,
            "onlyonce": False,
            "api_token": "",
            "ugnasurl": ""
        }


    def get_page(self) -> List[dict]:
        pass
   # 转移完成
    @eventmanager.register(EventType.TransferComplete )
    def send(self, event: Event):
        """
        通知绿联开始刷新媒体库
        """
        if not self._enabled or not self._ugnasurl or not self._api_token:
            return
        item = event.event_data
        if not item:
            return
       
            # 调用CSF下载字幕
        self.__request_reflush()

    def __request_csf(self):
         # 请求地址
        req_url = self._host+'?api_token'+self._api_token
        # 一个名称只建一个任务
        logger.info("通知绿联刷新媒体库")
        params = {}
        try:
            res = RequestUtils().post(req_url, json=params)
            if not res or res.status_code != 200:
                logger.error("调用绿联刷新媒体库API失败！")
            else:
                if res.msg:
                    logger.info("绿联刷新媒体库刷新：%s" % res.msg)
        except Exception as e:
            logger.error("绿联刷新媒体库出错：%s" + str(e))


    def stop_service(self):
        """
        退出插件
        """
        pass

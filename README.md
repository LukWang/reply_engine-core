# OPQBOT的回复管理引擎

## 简介

一个基于数据库的botoy群聊回复管理扩展

该项目稍作修改也可以直接作为botoy的单独插件使用，但更推荐作为模块通过在插件内调用的方式使用

所集成的功能有：
1. 基于关键词的公共问答管理（支持图片，文字，语音消息）
2. 基于关键词的私人问答管理（支持图片，文字）
3. 根据标签查找回复
4. 关键词同义词定义
5. 权限等级管理
6. 用户使用情况记录
7. 群聊插件管理 (作为单独插件时无法使用)

## 依赖

[botoy本体](https://github.com/opq-osc/botoy) 

```shell
pip install botoy -i https://pypi.org/simple --upgrade
```

[sqlite](https://www.sqlite.org/index.html)

对于ubuntu, debian等发行版可以直接使用下面的命令安装：

```shell
sudo apt install sqlite3
```

其他发行版可以根据自己的情况自行配置

## 配置方法

1. 克隆本仓库后，将本仓库的路径加入path
2. 进入该仓库的文件夹，将项目内的配置文件用例config.json.template虫命名为config.json, 并修改配置, 各项配置的说明如下
```shell
super_user         # bot主人的qq
pic_dir            # 用于存放下载图片的路径
voice_dir          # 用于存放语音回复的路径
private_limit      # 私聊回复与关键词的数量限制
user_record_level  # 用户行为记录的等级
db_schema          # 要使用的sqlite db文件
```
3. 运行目录下的db_setup.py构建数据库表结构
4. 配置botoy插件来使用该模块的功能, 你可以使用 [example](example/bot_reply_engine) 目录下的插件文件来快速配置

## 公共命令

公共命令是正常情况下群聊内所有人都可以使用的命令

### 存储回复

在群聊内发送："存回复 [关键词] [回复]" 来教机器人该怎么回复 (关键词内不可包含空格)

如： "存回复 在吗 不在"

如果附带图片，就可以存储图片回复

机器人下次在检测到对应的关键词后就会随机选择已经存储的回复

关键词的存储是跨群聊的

### 标签

如果想要利用标签来查找回复, 可以在关键词和回复之间插入 #标签 来存储带标签的回复, 标签内部也不可包含空格

如： "存回复 早安 #难过 不想起床.."

在群聊中通过"关键词 标签" 的方式呼出该回复

一个标签可以对应多条回复，随机抽取

### 同义词

可以通过定义同义词让不同的关键词使用另一关键词的回复

定义方式：在群聊在发送 "存同义词 [子关键词] [父关键词]" 来定义同义词

如： "存同义词 早上好 早安"

同义词是有层级关系的, 必须先定义父关键词, 然后让子关键词指向父关键词

### 语音回复

语音回复无法动态添加，需要使用者在voice_dir下手动添加音频文件，然后对机器人发送"_scanvoice"命令扫描音频文件来生成关键词和回复

voice_dir需要满足如下的文件结构

```
voice_dir ---- 关键词1 ----- 音频1.mp3
      |             | ----- 音频2.wav
      |                      ...
      |
      |   ---- 关键词2 ----- 音频1.mp3
      |
```
注：音频的文件名会作为回复标签存储下来, 以便使用标签查找对应的语音回复

### 私人回复

除了群聊中所有人都可以触发的关键词，你也可以定义机器人的私人关键词

区别于"存回复"命令, 你需要使用 "存私人回复" 命令来存储私人关键词和回复

并且需要通过@机器人的方式来触发关键词

一个用户可以存储的私人回复受到private_limit的限制

此外私人回复不支持标签

### 对话列表

你可以在群聊中发送 "对话列表" 来让机器人返回目前可用的公共关键词与你的私人关键词

## 管理命令

区别于公共命令, 管理命令只有super_user (一般设置成你自己) 可以使用, 目前支持的命令有:

重命名关键词：
_rename [关键词] [新名字]

禁用关键词：
禁用 [关键词]

启用关键词：
启用 [关键词]

注：关键词的禁用和启用是跨群聊的

设置用户权限等级(@想要设置的用户使用)
_setuser [数字等级]

设置关键词权限等级, 低于该等级的用户无法使用该关键词
_setcmd [关键词] [数字等级]

扫描音频目录的命令
_scanvoice

### 权限的补充说明

所有用户的数据将在初次使用命令/关键词或被设置权限时被创建, 关键词和用户的权限都被初始化为 1

如果使用_setuser 0 相当于禁止该用户使用任何命令和关键词, 除非你把某一个关键词的权限也设为 0

## 用户使用记录

数据库的user_records表记录了用户对每个关键词（以及插件，如果配置了的话）的使用次数

根据user_record_level的设置，记录的等级有三种：
0：不记录
1：关键词等级的记录
2：回复等级的记录

因为等级2的数据记录量可能太大, 默认的值一般是1

## 插件管理

通过使用[deco](reply_engine/deco)和[async_deco](reply_engine/async_deco)模块下的plugin_register装饰器, 就可以使用该项目的数据库来管理你的插件了

例：

```python
from reply_engine.deco import plugin_register

plugin_name = "插件1"
plugin_helper = "这是插件1的帮助说明"
@plugin_register(plugin_name, plugin_helper)
def group_msg_receiver(ctx):
    '''你的插件逻辑'''
```
使用该装饰器后, 插件的名字会作为一种特殊的关键词存储在数据库关键词表中（因此插件名字不能和其他关键词重复）

super_user可以通过在群聊发送"禁用"和"启用"命令来控制插件在群聊内的开和关

插件的控制等级是不跨群聊的，可以在机器人所在的每个群分别设置

对机器人发送命令“帮助”可以让机器人列出各项注册插件的名字

同时可以让用户发送帮助+插件名称来查看每个插件的具体帮助说明

如果在装饰器装饰的函数内返回正值, 装饰器还会在数据库中增加插件的使用记录

## 感谢

[xiyaowong/botoy](https://github.com/opq-osc/botoy)

[opq-osc/OPQ-SetuBot](https://github.com/opq-osc/OPQ-SetuBot)
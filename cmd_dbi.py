import sqlite3
import os, json
from enum import Enum
cur_file_dir = os.path.dirname(os.path.realpath(__file__))
db_schema = ''
try:
    with open(cur_file_dir + '/config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        db_schema = config['db_schema']
        db_schema = os.path.join(cur_file_dir, db_schema)
except:
    print('Fail to get db_schema info')


# enums
class CMD_TYPE:
    PIC = 1
    TEXT_TAG = 2
    TEXT_FORMAT = 4
    VOICE = 8


class cmdInfo:
    cmd_id: int
    orig_id: int
    cmd: str
    active: int
    cmd_type: int  # a bit map indicating supported reply type
    level: int  # permission level, default 1
    sequences: dict


class replyInfo:
    cmd_id: int
    type: int
    reply_id: int
    tag: str
    md5: str
    file_type: str
    reply: str


class aliasInfo:
    cmd_id: int
    cmd: str
    p_cmd_id: int
    active: int


class userInfo:
    user_id: int
    permission: int
    qq: str
    

class cmdDB:
    def __init__(self):
        self.conn = sqlite3.connect(db_schema, check_same_thread=False)
        self.db = self.conn.cursor()

    # alias operations
    def add_alias(self, new_cmd, parent, reply_type, level):
        self.db.execute("insert into cmd_alias(cmd, p_cmd_id, active, type, level, sequence_1, sequence_2, sequence_4, sequence_8) "
                                       "values(?,   ?,        1,      ?,    ?,     0, 0, 0, 0)", (new_cmd, parent, reply_type, level))
        self.conn.commit()
        return self.get_real_cmd(new_cmd)

    def make_parent(self, cmd):
        self.db.execute("update cmd_alias set p_cmd_id = 0 where cmd = ?", (cmd, ))

    def set_cmd_active(self, cmd, active):
        self.db.execute('update cmd_alias set active = ? where cmd = ?', (active, cmd))
        self.conn.commit()

    def get_all_cmd(self):
        cmds = []
        self.db.execute("select id, p_cmd_id, cmd, active, type, level, sequence_1, sequence_2, sequence_4, sequence_8 from cmd_alias where type < 1000 order by id")
        rows = self.db.fetchall()
        if rows is not None:
            for row in rows:
                cmd_info = cmdInfo()
                cmd_info.cmd_id = row[0]
                cmd_info.orig_id = row[1]
                cmd_info.cmd = row[2]
                cmd_info.active = row[3]
                cmd_info.cmd_type = row[4]
                cmd_info.level = row[5]
                cmd_info.sequences = {CMD_TYPE.PIC: row[6], CMD_TYPE.TEXT_TAG: row[7], CMD_TYPE.TEXT_FORMAT: row[8],
                                      CMD_TYPE.VOICE: row[9]}
                cmds.append(cmd_info)

        return cmds

    def set_cmd_seq(self, cmd_id, type_id, sequence_id):
        self.db.execute('update cmd_alias set sequence_{} = ? where id = ?'.format(type_id), (sequence_id, cmd_id))
        self.conn.commit()

    def set_cmd_type(self, cmd_id, reply_type):
        self.db.execute('update cmd_alias set type = ? where id = ?', (reply_type, cmd_id))
        self.conn.commit()

    def set_cmd_level(self, cmd_id, level):
        self.db.execute('update cmd_alias set level = ? where id = ?', (level, cmd_id))
        self.conn.commit()

    def get_real_cmd(self, cmd):
        orig_cmd_id = 0
        cmd_info = None
        self.db.execute("select id, p_cmd_id, active, type, level, sequence_1, sequence_2, sequence_4, sequence_8, cmd from cmd_alias where cmd = ?", (cmd,))
        row = self.db.fetchone()
        if row:
            orig_cmd_id = row[0]
        while row and row[1] > 0 and row[2] != 0:
            self.db.execute("select id, p_cmd_id, active, type, level, sequence_1, sequence_2, sequence_4, sequence_8, cmd from cmd_alias where id = ?", (row[1],))
            row = self.db.fetchone()
        if row:
            cmd_info = cmdInfo()
            cmd_info.cmd_id = row[0]
            cmd_info.orig_id = orig_cmd_id
            cmd_info.cmd = row[9]
            cmd_info.active = row[2]
            cmd_info.cmd_type = row[3]
            cmd_info.level = row[4]
            cmd_info.sequences = {CMD_TYPE.PIC: row[5], CMD_TYPE.TEXT_TAG: row[6], CMD_TYPE.TEXT_FORMAT: row[7],
                                  CMD_TYPE.VOICE: row[8]}
        return cmd_info

    # reply operation
    def add_reply(self, cmd_id, reply_type, reply_id, tag="", md5="", file_type="", reply="", user_id=0):
        self.db.execute('insert into replies(cmd_id,  type,       id,       tag, hash, file_type, reply, stamp,       user_id, time_used) '
                                      'values(?,      ?,          ?,        ?,   ?,    ?,         ?,     DATE("now"), ?,       0)',
                                             (cmd_id, reply_type, reply_id, tag, md5,  file_type, reply,              user_id))
        self.conn.commit()

    def get_reply(self, cmd_id, reply_type=0, reply_id=0, get_all=False, user_id=0):
        reply_info = None
        sql_str = "select type, id, tag, hash, file_type, reply from replies where cmd_id = ?"
        if reply_type > 0:
            sql_str += " and type = ?"
        else:
            sql_str += " and type > 0"
        if reply_id:
            sql_str += " and id = ?"

        if user_id > 0:
            sql_str += " and user_id = ?"

        if get_all:
            sql_str += " order by id"
        elif user_id > 0:
            sql_str += " order by time_used"

        arg_list = (cmd_id, reply_type, reply_id)
        if user_id > 0:
            arg_list += (user_id, )
        self.db.execute(sql_str, arg_list)
        if get_all:
            return self.db.fetchall()
        else:
            row = self.db.fetchone()
            if row:
                reply_info = replyInfo()
                reply_info.cmd_id = cmd_id
                reply_info.type = row[0]
                reply_info.reply_id = row[1]
                reply_info.tag = row[2]
                reply_info.md5 = row[3]
                reply_info.file_type = row[4]
                reply_info.reply = row[5]
        return reply_info

    def get_reply_by_tag(self, cmd_id, reply_type, tag, user_id=0):
        reply_info = None
        sql_str = "select id, tag, hash, file_type, reply from replies where cmd_id = ? and type = ? and tag like '" + tag + "%'"
        if user_id > 0:
            sql_str += " and user_id = ?"

        sql_str += " order by time_used"
        arg_list = (cmd_id,reply_type)
        if user_id > 0:
            arg_list += (user_id, )
        self.db.execute(sql_str, arg_list)
        row = self.db.fetchone()
        if row:
            reply_info = replyInfo()
            reply_info.cmd_id = cmd_id
            reply_info.type = reply_type
            reply_info.reply_id = row[0]
            reply_info.tag = row[1]
            reply_info.md5 = row[2]
            reply_info.file_type = row[3]
            reply_info.reply = row[4]
        return reply_info

    # user operations
    def add_user(self, user_qq):
        self.db.execute('insert into users(qq_id, first_used, permission) values(?, DATE("now"), ?)', (user_qq, 1))
        self.conn.commit()

    def get_user(self, user_qq):
        user_info = None
        self.db.execute('select user_id, permission from users where qq_id = ?', (user_qq,))
        row = self.db.fetchone()
        if row:
            user_info = userInfo()
            user_info.user_id = row[0]
            userInfo.permission = row[1]
            userInfo.qq = user_qq

        return user_info

    def set_user_permission(self, user_id, permission):
        self.db.execute('update users set permission=? where user_id=?', (permission, user_id))
        self.conn.commit()

    def used_inc(self, user_id, orig_id, cmd_id, reply_type, reply_id, private=False):
        reply_table = ""
        if private:
            reply_table = "p_replies"
        else:
            reply_table = "replies"
        self.db.execute('update {} set time_used = time_used + 1 where cmd_id = ? and type = ? and id = ?'.format(reply_table), (cmd_id, reply_type, reply_id))
        try:
            self.db.execute("insert into user_records(user_id, orig_cmd_id, cmd_id, type, reply_id, time_used, first_used, last_used) "
                                              "values(?,       ?,           ?,      ?,    ?,        1,          DATE('now'),DATE('now'))",
                                                     (user_id, orig_id, cmd_id, reply_type, reply_id))
        except sqlite3.DatabaseError:
            self.db.execute("update user_records set time_used = time_used + 1, last_used = DATE('now') "
                            "where user_id = ? and orig_cmd_id = ? and cmd_id = ? and type = ? and reply_id = ?",
                            (user_id, orig_id, cmd_id, reply_type, reply_id))

        self.conn.commit()

    def add_private_reply(self, cmd_id, reply_type, reply_id, user_id, md5="", file_type="", reply=""):
        self.db.execute('insert into p_replies(cmd_id,  type,       id,     hash, file_type, reply, stamp,       user_id, time_used) '
                                      'values(?,        ?,          ?,      ?,    ?,         ?,     DATE("now"), ?,       0)',
                                             (cmd_id,   reply_type, reply_id, md5, file_type, reply,              user_id))
        self.conn.commit()

    def get_private_reply_max_id(self, user_id, cmd_id):
        self.db.execute('select ifnull(max(id), 0) from p_replies where user_id = ? and cmd_id = ?', (user_id, cmd_id))
        return self.db.fetchone()[0]

    def get_private_reply(self, user_id, cmd_id):
        reply_info = None
        self.db.execute('select type, id, hash, file_type, reply from p_replies where user_id = ? and cmd_id = ? order by time_used', (user_id, cmd_id))
        row = self.db.fetchone()
        if row:
            reply_info = replyInfo()
            reply_info.cmd_id = cmd_id
            reply_info.type = row[0]
            reply_info.reply_id = row[1]
            reply_info.tag = ""
            reply_info.md5 = row[2]
            reply_info.file_type = row[3]
            reply_info.reply = row[4]
        return reply_info





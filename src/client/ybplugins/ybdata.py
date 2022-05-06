from peewee import *
from playhouse.migrate import SqliteMigrator, migrate

from .web_util import rand_string

_db = SqliteDatabase(None)
_version = 1  # 目前版本

MAX_TRY_TIMES = 5


class _BaseModel(Model):
    class Meta:
        database = _db


class Admin_key(_BaseModel):
    key = TextField(primary_key=True)
    valid = BooleanField()
    key_used = BooleanField()
    cookie = TextField(index=True)
    create_time = TimestampField()


class User(_BaseModel):
    qqid = BigIntegerField(primary_key=True)
    nickname = TextField(null=True)

    # 1:主人 10:公会战管理员 100:成员
    authority_group = IntegerField(default=100)

    privacy = IntegerField(default=MAX_TRY_TIMES)   # 密码错误次数
    clan_group_id = BigIntegerField(null=True)
    last_login_time = BigIntegerField(default=0)
    last_login_ipaddr = IPField(default='0.0.0.0')
    password = FixedCharField(max_length=64, null=True)
    must_change_password = BooleanField(default=True)
    login_code = FixedCharField(max_length=6, null=True)
    login_code_available = BooleanField(default=False)
    login_code_expire_time = BigIntegerField(default=0)
    salt = CharField(max_length=16, default=rand_string)
    deleted = BooleanField(default=False)


class User_login(_BaseModel):
    qqid = BigIntegerField()
    auth_cookie = FixedCharField(max_length=64)
    auth_cookie_expire_time = BigIntegerField(default=0)
    last_login_time = BigIntegerField(default=0)
    last_login_ipaddr = IPField(default='0.0.0.0')

    class Meta:
        primary_key = CompositeKey('qqid', 'auth_cookie')

#原谅我mongodb用习惯了
class Clan_group(_BaseModel):
    group_id = BigIntegerField(primary_key=True)
    group_name = TextField(null=True)
    privacy = IntegerField(default=2)  # 0x1：允许游客查看出刀表，0x2：允许api调用出刀表
    game_server = CharField(max_length=2, default='cn')
    notification = IntegerField(default=0xffff)     #需要接收的通知
    battle_id = IntegerField(default=0)             #档案号
    apikey = CharField(max_length=16, default=rand_string)
    threshold = IntegerField(default=4000000)       #伤害阈值，计算分数用

    boss_cycle = SmallIntegerField(default=1)       #现周目数

    now_cycle_boss_health = TextField(default='')   #现周目boss剩余血量（json格式文本）
    #结构 {boss_num:血量, }
    next_cycle_boss_health = TextField(default='')  #下周目boss剩余血量（json格式文本）

    #所有正在出刀的人（json格式文本）
    #结构：{boss_num:{
    #           challenger:{
    #               is_continue:是否是补偿,
    #               behalf:代刀人qq,
    #               s:余秒,
    #               damage:报伤害,
    #               tree:是否挂树boolean,
    #               msg:挂树留言
    #           }, 
    #       }, }
    challenging_member_list = TextField(null=True)

    #预约表（json格式文本） 结构：{boss_num:[qqid, ], }
    subscribe_list = TextField(null=True)

    challenging_start_time = BigIntegerField(default=0)
    deleted = BooleanField(default=False)

class Clan_group_backups(_BaseModel):
    group_id = BigIntegerField(index=True)
    battle_id = IntegerField(index=True)             #档案号
    group_data = TextField(null=True)   #所有数据（json格式文本） 结构同Clan_group

    class Meta:
        primary_key = CompositeKey('group_id', 'battle_id')


class Clan_member(_BaseModel):
    group_id = BigIntegerField(index=True)
    qqid = BigIntegerField(index=True)
    role = IntegerField(default=100)
    last_save_slot = IntegerField(null=True)    #上一次sl的日期
    remaining_status = TextField(null=True)

    class Meta:
        primary_key = CompositeKey('group_id', 'qqid')


#每一刀的报刀数据
class Clan_challenge(_BaseModel):
    cid = AutoField(primary_key=True)       #自增id
    bid = IntegerField(default=0)           #档案号
    gid = BigIntegerField()                 #公会qq群号
    qqid = BigIntegerField(index=True)      #出刀人qq号
    challenge_pcrdate = IntegerField()      #出刀时的日期
    challenge_pcrtime = IntegerField()      #出刀时的时间
    boss_cycle = SmallIntegerField()        #第几周目
    boss_num = SmallIntegerField()          #几王
    boss_health_remain = BigIntegerField()  #boss剩余血量
    challenge_damage = BigIntegerField()    #对boss造成的伤害
    is_continue = BooleanField()            #是否是补偿刀
    message = TextField(null=True)          #信息
    behalf = IntegerField(null=True)        #代刀人

    class Meta:
        indexes = (
            (('bid', 'gid'), False),
            (('qqid', 'challenge_pcrdate'), False),
            (('bid', 'gid', 'challenge_pcrdate'), False),
        )


class Character(_BaseModel):
    chid = IntegerField(primary_key=True)
    name = CharField(max_length=64)
    frequent = BooleanField(default=True)


class Chara_nickname(_BaseModel):
    name = CharField(max_length=64, primary_key=True)
    chid = IntegerField()



class DB_schema(_BaseModel):
    key = CharField(max_length=64, primary_key=True)
    value = TextField()


def init(sqlite_filename):
    _db.init(
        database=sqlite_filename,
        pragmas={
            'journal_mode': 'wal',
            'cache_size': -1024 * 64,
        },
    )

    old_version = 1
    if not DB_schema.table_exists():
        DB_schema.create_table()
        DB_schema.create(key='version', value=str(_version))
    else:
        old_version = int(DB_schema.get(key='version').value)

    if not User.table_exists():
        Admin_key.create_table()
        User.create_table()
        User_login.create_table()
        Clan_group.create_table()
        Clan_member.create_table()
        Clan_group_backups.create_table()
        Clan_challenge.create_table()
        Character.create_table()
        old_version = _version
    if old_version > _version:
        print('数据库版本高于程序版本，请升级yobot')
        raise SystemExit()
    if old_version < _version:
        print('正在升级数据库')
        db_upgrade(old_version)
        print('数据库升级完毕')


def db_upgrade(old_version):
    migrator = SqliteMigrator(_db)
    if old_version < 2:
        pass
    
    
    DB_schema.replace(key='version', value=str(_version)).execute()

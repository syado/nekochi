import asyncio
import base64
import csv
import datetime 
import json
import random
import re
from ctypes.util import find_library
from time import sleep
import discord
import requests
from discord import opus
import sysv_ipc

rget = requests.get

f = open("config.json", encoding='utf-8')
config = json.load(f)
f.close()
f = open("weathercode.json", encoding='utf-8')
weathercode = json.load(f)
f.close()

client = discord.Client()
send = client.send_message
edit = client.edit_message
token = config["discord"]["token"]
sm = config["SharedMemory"]
memory = sysv_ipc.SharedMemory(int(sm["key"],16), flags=sysv_ipc.IPC_CREAT, mode=int(sm["mode"],8), size=sm["size"])

exchange_num = config["exchange_num"]
admin_id = config["admin_id"]

JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

def get_Weather(lot,lat):
    appid = config["openweathermap"]["key"]
    output = "json"
    url = "http://api.openweathermap.org/data/2.5/weather?"
    url += "APPID=" + appid
    url += "&lat=" + lat
    url += "&lon=" + lot
    url += "&units=" + "metric" 
    r = rget(url)
    res = r.json()
    return res

def get_Coordinates(location_name):
    appid = config["yahoo"]["appid"]
    output = "json"
    query = location_name
    url = "https://map.yahooapis.jp/geocode/V1/geoCoder?"
    url += "appid=" + appid
    url += "&output=" + output
    url += "&query=" + query
    r = rget(url)
    res = r.json()
    return res["Feature"][0]["Geometry"]["Coordinates"]

def get_Weather_info(location_name):
    reslist = get_Coordinates(location_name).split(",")
    weather = get_Weather(reslist[0],reslist[1])
    em = discord.Embed(colour=0x3498db)
    em.add_field(name="天気", value=weathercode[str(weather["weather"][0]["id"])], inline=True)
    em.add_field(name="気温", value=str(int(weather["main"]["temp"]))+'°C', inline=True)
    em.add_field(name="湿度", value=str(weather["main"]["humidity"])+'％', inline=True)
    em.add_field(name="風速", value=str(weather["wind"]["speed"])+'m', inline=True)
    em.set_author(
        name=location_name+'の気象情報', 
        icon_url='https://upload.wikimedia.org/wikipedia/commons/1/15/OpenWeatherMap_logo.png'
        )
    em.set_thumbnail(url='http://openweathermap.org/img/w/' + weather["weather"][0]["icon"].replace('n', 'd') +'.png')
    return em

def mem_read(byte2, byte1):
    return memory.read(byte1, byte2).decode("utf-8")

def mem_write(data, byte2, byte1):
    if isinstance(data, str):
        data = '{0:<{1}}'.format(data, byte1)
    else:
        data = '{0:>{1}}'.format(data, byte1)
    return memory.write(data, byte2)

def zaif_last(pair: str):
    zaif_url = 'https://api.zaif.jp/api/1/last_price/'
    try:
        json = rget(zaif_url + pair).json()
        last_price = json['last_price']
        if(pair[-3:] == "btc"):
            outstr = str('{:.8f}'.format(last_price))
        elif(pair[-3:] == "jpy"):
            outstr = "{0:>9}".format(str(last_price))
    except:
        outstr = "{0:<9}".format("error")
    return outstr
    
def cc_last(pair: str):
    cc_url = 'https://coincheck.com/api/rate/'
    try:
        json = rget(cc_url + pair).json()
        last_price = float(json['rate'])
        if(pair[-3:] == "btc"):
            outstr = str('{:.8f}'.format(last_price))
        elif(pair[-3:] == "jpy"):
            outstr = "{0:>9}".format(str('{:.2f}'.format(last_price)))
    except:
        outstr = "{0:<9}".format("error")
    return outstr

def datetimestr():
    return datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")



def echo(cmdstr):
    print(datetime.datetime.now().strftime("%H:%M:%S ") + cmdstr)

async def delete_message(message):
    try:
        await client.delete_message(message)
    except:
        #await send(message.channel, "削除する権限がありません")
        pass

#起動時のみ実行
@client.event
async def on_ready():


    #起動確認
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):
    global vc, yomi_user, jisyo, yomi_channel, admin_id, exchange_num

    #メッセージをスペースごとに区切って格納
    messagelist = message.content.split()
    print(message.content)

    cmd = []
    f = open("cmd.csv", "r")
    dataReader = csv.reader(f)
    for row in dataReader:
       cmd.append(row)
    f.close()

    if len(messagelist) == 2:
        if messagelist[0] == "天気":
            location_name = messagelist[1]
            em = get_Weather_info(location_name)
            return await send(message.channel,embed=em)

        if messagelist[1] == "天気":
            location_name = messagelist[0]
            em = get_Weather_info(location_name)
            return await send(message.channel,embed=em)
        
        if messagelist[0] == "ステ" and admin_id == message.author.id:
            await delete_message(message)
            if client.user != message.author:
                await client.change_presence(game=discord.Game(name=messagelist[1]))
                return await send(message.channel, "ステータス更新")
    
        if messagelist[0] == "nick" and admin_id == message.author.id:
            await delete_message(message)
            if client.user != message.author:
                await client.change_nickname(message.server.me, messagelist[1])
                return await send(message.channel, "ニックネーム変更")

        if messagelist[0] == "gox":
            await delete_message(message)
            m = messagelist[1] + 'はGOXしました' 
            return await send(message.channel, m) 
        
        if messagelist[1] == "gox":
            await delete_message(message)
            m = messagelist[0] + 'はGOXしました' 
            return await send(message.channel, m) 

    for i in range(len(cmd)):
        if message.content.startswith(cmd[i][0]) and message.author.id != client.user.id:
            m = cmd[i][1]
            while True:
                r = re.search(r"<name>", m)
                if r:
                    m = cmd[i][1].replace(r.group(), message.author.name)
                else:
                    break
            return await send(message.channel, m)

    if messagelist[0] in {"スロット", "すろっと"}:
        await delete_message(message)
        random_list = [":green_apple:",":apple:",":pear:",":tangerine:",":lemon:",":banana:",":watermelon:",":grapes:",":strawberry:",":melon:"]
        author = str(message.author.mention) + " "

        for i in range(10):
            if i == 0:
                m = author
                for r in range(3):
                    m += "\n" + random.choice(random_list) + random.choice(random_list) + random.choice(random_list) 
                m1 = await send(message.channel, m)

            elif i == 9:
                m = author
                for r in range(3):
                    m += "\n" + random.choice(random_list) + random.choice(random_list) + random.choice(random_list) 
                return await edit(m1, m)

            else:
                m = author
                for r in range(3):
                    m += "\n" + random.choice(random_list) + random.choice(random_list) + random.choice(random_list) 
                m1 = await edit(m1, m)

            sleep(0.1)
    
    if messagelist[0].lower() in {"all"}:
        await delete_message(message)
        name = []
        last = []
        ask = []
        bid = []
        diff = []
        vol = []
        outstr = "```js\n"
        outstr += "{:<{}}{:>{}}{:>{}}{:>{}}{:>{}}{:>{}}\n".format('name',10,'last',10,'ask',10,'diff',6,'bid',10,'vol',8)
        n = 0
        for i in exchange_num:
            name.append(str.strip(mem_read(i * 50000 + 0, 15)))
            last.append(str.strip(mem_read(i * 50000 + 30, 10)))
            ask.append(str.strip(mem_read(i * 50000 + 40, 10)))
            bid.append(str.strip(mem_read(i * 50000 + 50, 10)))
            diff.append(int(ask[n]) - int(bid[n]))
            vol.append(str.strip(mem_read(i * 50000 + 60, 10)))
            outstr += "{:<{}}{:>{}}{:>{}}{:>{}}{:>{}}{:>{}}\n".format(name[n],10,last[n],10,ask[n],10,diff[n],6,bid[n],10,vol[n],8)
            n = n + 1
        outstr += datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
        outstr += "```"
        m = await edit(await send(message.channel, "``` ```"), outstr)

        if len(messagelist) == 2:
            if messagelist[1].isdigit():
                if int(messagelist[1]) > 100: 
                    messagelist[1] = 100
                for j in range(int(messagelist[1])):
                    sleep(1)
                    outstr = "```js\n"
                    outstr += "{:<{}}{:>{}}{:>{}}{:>{}}{:>{}}{:>{}}\n".format('name',10,'last',10,'ask',10,'diff',6,'bid',10,'vol',8)
                    n = 0
                    for i in exchange_num:
                        name[n] = str.strip(mem_read(i * 50000 + 0, 15))
                        last[n] = str.strip(mem_read(i * 50000 + 30, 10))
                        ask[n] = str.strip(mem_read(i * 50000 + 40, 10))
                        bid[n] = str.strip(mem_read(i * 50000 + 50, 10))
                        diff[n] = int(ask[n]) - int(bid[n])
                        vol[n] = str.strip(mem_read(i * 50000 + 60, 10))
                        outstr += "{:<{}}{:>{}}{:>{}}{:>{}}{:>{}}{:>{}}\n".format(name[n],10,last[n],10,ask[n],10,diff[n],6,bid[n],10,vol[n],8)
                        n = n + 1
                
                    outstr += datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    outstr += "```\n"
                    outstr += "cnt:" + str(j+1) + "/" + str(messagelist[1])
                    m = await edit(m, outstr)

    if messagelist[0] in {"相場", "そうば"}:
        await delete_message(message)
        btc = float(str.strip(mem_read(4 * 50000 + 130, 10)))
        jpy = float(str.strip(mem_read(4 * 50000 + 140, 10)))
        av60 = float(str.strip(mem_read(4 * 50000 + 295, 15)))
        av240 = float(str.strip(mem_read(4 * 50000 + 325, 15)))
        last = float(str.strip(mem_read(4 * 50000 + 30, 10)))
        if btc * last < jpy:
            m = "さがるにゃん\n"
        else:
            m = "あがるにゃん\n"
        m1 = await send(message.channel, m)
        sa = int(av60 / 60 - av240 / 240)
        m += "ねこっっち指数:" + str(sa) + "\n"
        m += datetimestr()
        m1 = await edit(m1, m) 
        if len(messagelist) >= 2:
            if messagelist[1].isdigit():
                if int(messagelist[1]) > 100: 
                    messagelist[1] = 100
                for j in range(int(messagelist[1])):
                    sleep(1)
                    btc = float(str.strip(mem_read(4 * 50000 + 130, 10)))
                    jpy = float(str.strip(mem_read(4 * 50000 + 140, 10)))
                    av60 = float(str.strip(mem_read(4 * 50000 + 295, 15)))
                    av240 = float(str.strip(mem_read(4 * 50000 + 325, 15)))
                    last = float(str.strip(mem_read(4 * 50000 + 30, 10)))
                    if btc * last < jpy:
                        m = "さがるにゃん\n"
                    else:
                        m = "あがるにゃん\n"
                    m += "ねこっっち指数:" + str(int(av60 / 60 - av240 / 240))+ "\n"
                    m += datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    m += "\ncnt:" + str(j+1)
                    return await edit(m1, m)

    if messagelist[0].lower() in {"bfss"}:
        await delete_message(message)
        bf = rget('https://lightning.bitflyer.jp/v1/gethealth').json()
        m = "Bitflyer Server Status:" + bf["status"] + '\n'
        m += datetimestr()
        return await send(message.channel, m)

    if messagelist[0].lower() in {"cc"}:
        await delete_message(message)

        m = '```js\n'
        m += 'CC通貨価格\n'
        m += '--------------------+---------------\n'
        m += 'btc : ' + cc_last("btc_jpy") + ' JPY | \n'
        for i in ["eth","etc","lsk","fct","xrp","xem","ltc","bch"]:
            m += i+' : ' + cc_last(i+"_jpy") + ' JPY | ' + cc_last(i+"_btc") + ' BTC\n'
        m += datetimestr()
        m += '```'
        return await edit(await send(message.channel, "``` ```"), m)

    if messagelist[0].lower() in {"bf"}:
        await delete_message(message)
        bf = 'https://lightning.bitflyer.jp/v1/ticker?product_code='
        b_btc_jpy  = "{0:>10}".format(str(rget(bf + 'BTC_JPY').json()['ltp']))
        b_fx_btc_jpy = "{0:>10}".format(str(rget(bf + 'FX_BTC_JPY').json()['ltp']))
        b_bch_btc = str('{:.8f}'.format(rget(bf + 'BCH_BTC').json()['ltp']))
        b_eth_btc = str('{:.8f}'.format(rget(bf + 'ETH_BTC').json()['ltp']))

        bf_s = rget('https://lightning.bitflyer.jp/v1/gethealth').json()["status"]

        m = '```js\n'
        m += 'bitflyer : ' + bf_s +'\n'
        m += '---------------------\n'
        m += 'btc : ' + b_btc_jpy + ' JPY\n'
        m += 'fx  : ' + b_fx_btc_jpy + ' JPY\n'
        m += 'bch : ' + b_bch_btc + ' BTC\n'
        m += 'eth : ' + b_eth_btc + ' BTC\n'
        m += datetimestr()
        m += '```'
        return await edit(await send(message.channel, "``` ```"), m)

    if messagelist[0].lower() in {"zaif"}:
        await delete_message(message)

        m = '```js\n'
        m += 'Zaif通貨価格\n'
        m += '--------------------+---------------\n'
        m += 'btc : ' + zaif_last('btc_jpy') + ' JPY | ' + str('{:.8f}'.format(1)) + ' BTC\n'
        for i in ["bch","eth","xem","mona","zaif"]:            
            m += i+' : ' + zaif_last(i+'_jpy') + ' JPY | ' + zaif_last(i+'_btc') + ' BTC\n'
        m += 'Ecms: ' + zaif_last('erc20.cms_jpy') + ' JPY |\n'
        m += 'Xcms: ' + zaif_last('mosaic.cms_jpy') + ' JPY |\n'
        m += datetimestr()
        m += '```'
        return await edit(await send(message.channel, "``` ```"), m)

    if messagelist[0].lower() in {"polo"}:
        await delete_message(message)
        coin = messagelist[1].upper()
        Polo = 'https://poloniex.com/public?command=returnTicker'

        polo_json = rget(Polo).json()
        last = float(polo_json[coin]['last'])
        h24 = float(polo_json[coin]['high24hr'])
        l24 = float(polo_json[coin]['low24hr'])
  
        last = '{:.8f}'.format(last) #小数第8桁まで表示するように変換
        h24 = '{:.8f}'.format(h24)
        l24 = '{:.8f}'.format(l24) 
    
        per = float(polo_json[coin]['percentChange'])
    
        per = round((per * 100), 2)

        m = '```\n'
        m += 'poloniexの' + coin + '価格\n'
        m += '---------------------------\n'
        m += '変動：　' + str(per) + ' %\n'
        m += '---------------------------\n'
        m += '価格：　' + str(last) + '\n'
        m += '最高：　' + str(h24) + '\n'
        m += '最安：　' + str(l24) + '\n'
        m += datetimestr()
        m += '```'

        coin = ''
        return await send(message.channel, m)

    if messagelist[0].lower() in {"se"}:
        await delete_message(message)
        coin = messagelist[1].upper()
        coin_url = 'https://stocks.exchange/api2/ticker'
        bf = 'https://lightning.bitflyer.jp/v1/ticker?product_code=BTC_JPY'
        btcjpy = float(rget(bf).json()['ltp'])
        coin_json = rget(coin_url).json()
        for i in range(50):
            if coin_json[i]["market_name"] == coin + "_BTC":
                last_btc = float(coin_json[i]["last"])
                break

        last_jpy = '{:.2f}'.format(last_btc * btcjpy)       
        last_btc = '{:.1f}'.format(last_btc * 100000000)
        m = '```\n'
        m += coin + '_BTCの価格 (stocks.exchange参照)\n'
        m += 'BTC：' + "{0:>7}".format(last_btc) + ' ｻﾄｼ\n'
        m += 'JPY：' + "{0:>7}".format(last_jpy) + ' 円\n'
        m += datetimestr()
        m += '```'

        coin = ''
        return await send(message.channel, m)

    if messagelist[0].lower() in {"usd"}:
        usd_url = 'https://www.gaitameonline.com/rateaj/getrate'
        usd_json = rget(usd_url).json()
        for i in range(30):
            if usd_json["quotes"][i]["currencyPairCode"] == "USDJPY":
                bid = float(usd_json["quotes"][i]["bid"])
                ask = float(usd_json["quotes"][i]["ask"])
                last = (bid + ask) / 2
                break
        m = '```\n'
        m += 'USD/JPYの価格\n'
        m += "{0:>7.3f}".format(last) + ' 円\n'
        m += '```'

        coin = ''
        return await send(message.channel, m)

    if messagelist[0] in {"サイコロ", "さいころ", "ダイス", "だいす"}:
        random_list = [":one:",":two:",":three:",":four:",":five:",":six:"]
        author = str(message.author.mention) + " "
        m = author + "\n" + random.choice(random_list)
        try:
            if int(messagelist[1]) <= 10:
                for j in range(int(messagelist[1]) - 1):
                    m += " " + random.choice(random_list)
            else:
                m = "個数が多すぎるにゃん"
        except:
            pass
        return await send(message.channel, m)
    
    if messagelist[0] in {"コイン", "こいん"}:
        random_list = ["裏","表"]
        author = str(message.author.mention) + " "
        m = author + "\n" + random.choice(random_list)
        return await send(message.channel, m)


    if messagelist[0].lower() in {"help"}:
        await delete_message(message)
        m = "ねこっっちの飼い慣らし方は秘密\n"
        m += "飼い主は<@161524945392893952>\n"
        return await send(message.channel, m)

if __name__ == "__main__":
    client.run(token)

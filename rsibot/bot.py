import websocket, json, pprint, talib, numpy
import config
from binance.client import Client
from binance.enums import *

SOCKET = "wss://stream.binance.com:9443/ws/dogeusdt@kline_1m"


TRADE_SYMBOL = 'DOGEUSD'
TRADE_QUANTITY = 50

client = Client(config.API_KEY, config.API_SECRET, tld='us')

def get_historical_closes():
    klines = client.get_historical_klines(TRADE_SYMBOL, Client.KLINE_INTERVAL_1MINUTE, "30 minutes ago UTC")
    return list(map(lambda x: float(x[4]), klines))

closes = get_historical_closes()
print(closes)

# position info
in_position = False
position_price = 0
total_profit = 0

def get_stoch_rsi_signal(np_closes):
    STOCH_RSI_PERIOD = 14
    STOCH_K_PERIOD = 5
    STOCH_D_PERIOD = 3
    STOCH_D_MATYPE = 0
    fastk, fastd = talib.STOCHRSI(np_closes, STOCH_RSI_PERIOD, STOCH_K_PERIOD, STOCH_D_PERIOD, STOCH_D_MATYPE)
    # print("stoch rsi - k: {} d: {}".format(fastk, fastd))

    print("the current stoch rsi - k: {} d: {}".format(fastk[-1], fastd[-1]))

    if fastk[-1] > fastd[-1] and fastd[-1] < 80:
        return SIDE_BUY
    elif fastk[-1] < fastd[-1] and fastk[-1] > 20:
        return SIDE_SELL
    else:
        return None

def get_rsi_signal(np_closes):
    RSI_PERIOD = 14
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    rsi = talib.RSI(np_closes, RSI_PERIOD)
    #print("rsi: {}".format(rsi))
    last_rsi = rsi[-1]
    print("the current rsi is {}".format(last_rsi))

    if last_rsi < RSI_OVERSOLD:
        return SIDE_SELL
    elif last_rsi > RSI_OVERBOUGHT:
        return SIDE_BUY

def get_macd_signal(np_closes):
    FAST_PERIOD = 12
    SLOW_PERIOD = 26
    SIGNAL_PERIOD = 9
    macd, macdsignal, macdhist = talib.MACD(np_closes, FAST_PERIOD, SLOW_PERIOD, SIGNAL_PERIOD)
    # print("macd: {} macdsignal: {} macdhist: {}".format(macd, macdsignal, macdhist))
    print("current macd: {} macdsignal: {} macdhist: {}".format(macd[-1], macdsignal[-1], macdhist[-1]))

    if macd[-1] > macdsignal[-1]:
        return SIDE_BUY
    elif macd[-1] < macdsignal[-1]:
        return SIDE_SELL

def order(side, quantity, symbol, order_type=ORDER_TYPE_MARKET):
    try:
        print("sending order")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        print(order)

    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return True
    
def on_open(ws):
    print('opened connection')

def on_close(ws):
    print('closed connection')

def on_message(ws, message):
    
    # print('received message')
    json_message = json.loads(message)
    # pprint.pprint(json_message)

    candle = json_message['k']

    is_candle_closed = candle['x']
    close = candle['c']

    if is_candle_closed:
        print("candle closed at {}".format(close))
        closes.append(float(close))
        # print("closes: {}".format(closes))

        np_closes = numpy.array(closes)
        stoch_signal = get_stoch_rsi_signal(np_closes)
        print("stoch signal: {}".format(stoch_signal))
        # rsi_signal = get_rsi_signal(np_closes)
        macd_signal = get_macd_signal(np_closes)
        print("macd signal: {}".format(macd_signal))


        if(not in_position and stoch_signal == SIDE_BUY and macd_signal == SIDE_BUY):
            print("BUY SIGNAL")
            order_succeeded = order(SIDE_BUY, TRADE_QUANTITY, TRADE_SYMBOL, ORDER_TYPE_MARKET)
            if order_succeeded:
                in_position = True
        elif (in_position and (stoch_signal == SIDE_SELL or macd_signal == SIDE_SELL)):
            print("SELL SIGNAL stoch: {} macd_signal: {}".format(stoch_signal, macd_signal))
            order_succeeded = order(SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL, ORDER_TYPE_MARKET)
            if order_succeeded:
                in_position = False
                
ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()
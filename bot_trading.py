import pandas as pd
import ta
from binance.client import Client

# Configurar API Key e Secret Key (substituir pelos seus dados)
API_KEY = ""
API_SECRET = ""

# Criar cliente Binance
client = Client(API_KEY, API_SECRET)

# Configurações globais
SYMBOL = "BTCUSDT"  # Par de negociação
TIMEFRAME = Client.KLINE_INTERVAL_5MINUTE  # Timeframe de 5 minutos
CANDLE_LIMIT = 50  # Número de candles a buscar

def obter_dados_historicos(symbol, timeframe, limit):
    """ Obtém dados de mercado da Binance e retorna um DataFrame """
    candles = client.get_klines(symbol=symbol, interval=timeframe, limit=limit)
    
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume",
                                        "close_time", "quote_asset_volume", "number_of_trades",
                                        "taker_buy_base", "taker_buy_quote", "ignore"])
    
    # Converter colunas para números
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
    
    return df

def calcular_indicadores(df):
    """ Calcula Médias Móveis e RSI e adiciona ao DataFrame """
    
    # Calcular Média Móvel Curta (9 períodos)
    df["SMA9"] = df["close"].rolling(window=9).mean()

    # Calcular Média Móvel Longa (21 períodos)
    df["SMA21"] = df["close"].rolling(window=21).mean()

    # Calcular RSI com janela de 14 períodos
    df["RSI"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

    # Remover linhas iniciais com NaN (necessário por causa do rolling window)
    df.dropna(inplace=True)

    return df

def verificar_sinais(df):
    """ Verifica sinais de compra e venda e informa quais critérios foram atingidos """

    if df.empty:
        print("❌ ERRO: DataFrame vazio após remoção de valores NaN.")
        return

    # Últimos valores dos indicadores
    ultima_sma9 = df["SMA9"].iloc[-1]
    ultima_sma21 = df["SMA21"].iloc[-1]
    penultima_sma9 = df["SMA9"].iloc[-2]
    penultima_sma21 = df["SMA21"].iloc[-2]
    ultimo_rsi = df["RSI"].iloc[-1]

    print("\n📊 Indicadores Atuais:")
    print(f"SMA9 Atual: {ultima_sma9:.2f} | SMA21 Atual: {ultima_sma21:.2f}")
    print(f"SMA9 Anterior: {penultima_sma9:.2f} | SMA21 Anterior: {penultima_sma21:.2f}")
    print(f"RSI Atual: {ultimo_rsi:.2f}\n")

    # 📌 Verificar os critérios separadamente
    cruzamento_compra = ultima_sma9 > ultima_sma21 and penultima_sma9 <= penultima_sma21
    cruzamento_venda = ultima_sma9 < ultima_sma21 and penultima_sma9 >= penultima_sma21
    rsi_compra = ultimo_rsi < 30
    rsi_venda = ultimo_rsi > 70

    # 📌 Relatório de verificação dos critérios
    print("🛠️ Verificação dos Critérios:\n")

    # Médias Móveis
    if cruzamento_compra:
        print("✅ Critério de COMPRA pelas Médias Móveis atingido (SMA9 cruzou acima da SMA21).")
    else:
        print("❌ Critério de COMPRA pelas Médias Móveis NÃO atingido.")

    if cruzamento_venda:
        print("✅ Critério de VENDA pelas Médias Móveis atingido (SMA9 cruzou abaixo da SMA21).")
    else:
        print("❌ Critério de VENDA pelas Médias Móveis NÃO atingido.")

    # RSI
    if rsi_compra:
        print("✅ Critério de COMPRA pelo RSI atingido (RSI < 30).")
    else:
        print(f"❌ Critério de COMPRA pelo RSI NÃO atingido (RSI atual: {ultimo_rsi:.2f}).")

    if rsi_venda:
        print("✅ Critério de VENDA pelo RSI atingido (RSI > 70).")
    else:
        print(f"❌ Critério de VENDA pelo RSI NÃO atingido (RSI atual: {ultimo_rsi:.2f}).")

    # 📌 Critério de Entrada (Comprar)
    if cruzamento_compra and rsi_compra:
        print("\n✅ Sinal de COMPRA confirmado: Médias Móveis e RSI atingiram os critérios!\n")
    else:
        print("\n⚠️ Sinal de COMPRA NÃO confirmado: Faltam critérios para ativar a compra.\n")

    # 📌 Critério de Saída (Vender)
    if cruzamento_venda or rsi_venda:
        print("🚨 Sinal de VENDA confirmado: Um dos critérios de venda foi atingido!\n")
    else:
        print("⚠️ Sinal de VENDA NÃO confirmado: Faltam critérios para ativar a venda.\n")


def obter_preco_atual(symbol):
    """ Obtém o preço atual do ativo """
    ticker = client.get_symbol_ticker(symbol=symbol)
    preco_atual = float(ticker["price"])
    print(f"\n💰 Preço Atual do {symbol}: {preco_atual:.2f}\n")
    return preco_atual

# EXECUÇÃO
df = obter_dados_historicos(SYMBOL, TIMEFRAME, CANDLE_LIMIT)
df = calcular_indicadores(df)
obter_preco_atual(SYMBOL)
verificar_sinais(df)



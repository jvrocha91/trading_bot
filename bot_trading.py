import pandas as pd
import ta
from binance.client import Client
import time

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


# Variável global para evitar ordens duplicadas
ultima_ordem = None

def verificar_saldo():
    """ Obtém os saldos disponíveis em USDT e BTC para negociação. """
    try:
        saldo_usdt = float(client.get_asset_balance(asset="USDT")["free"])
        saldo_btc = float(client.get_asset_balance(asset="BTC")["free"])
        
        print(f"\n💰 Saldo Atual:")
        print(f"  - USDT disponível: {saldo_usdt:.2f} USDT")
        print(f"  - BTC disponível: {saldo_btc:.6f} BTC\n")
        
        return saldo_usdt, saldo_btc
    except Exception as e:
        print(f"❌ Erro ao obter saldo: {e}")
        return 0, 0


def comprar(qtd_btc):
    """ Executa uma ordem de compra de BTC com a quantidade especificada. """
    global ultima_ordem
    try:
        saldo_usdt, saldo_btc = verificar_saldo()
        preco_atual = obter_preco_atual(SYMBOL)

        if saldo_usdt < preco_atual * qtd_btc:
            print("❌ Saldo insuficiente para compra!")
            return

        # Criar ordem de compra
        ordem = client.order_market_buy(symbol=SYMBOL, quantity=qtd_btc)
        ultima_ordem = "compra"

        print(f"\n✅ Ordem de COMPRA executada! Quantidade: {qtd_btc} BTC\n")
        print(ordem)

        # Exibir saldo atualizado
        verificar_saldo()
    except Exception as e:
        print(f"❌ Erro ao executar COMPRA: {e}")


def vender(qtd_btc):
    """ Executa uma ordem de venda de BTC com a quantidade especificada. """
    global ultima_ordem
    try:
        saldo_usdt, saldo_btc = verificar_saldo()

        if saldo_btc < qtd_btc:
            print("❌ Saldo insuficiente para venda!")
            return

        # Criar ordem de venda
        ordem = client.order_market_sell(symbol=SYMBOL, quantity=qtd_btc)
        ultima_ordem = "venda"

        print(f"\n✅ Ordem de VENDA executada! Quantidade: {qtd_btc} BTC\n")
        print(ordem)

        # Exibir saldo atualizado
        verificar_saldo()
    except Exception as e:
        print(f"❌ Erro ao executar VENDA: {e}")


def executar_ordem(df):
    """ Executa compra ou venda baseada nos sinais detectados. """
    global ultima_ordem

    # Últimos valores dos indicadores
    cruzamento_compra = df["SMA9"].iloc[-1] > df["SMA21"].iloc[-1] and df["SMA9"].iloc[-2] <= df["SMA21"].iloc[-2]
    cruzamento_venda = df["SMA9"].iloc[-1] < df["SMA21"].iloc[-1] and df["SMA9"].iloc[-2] >= df["SMA21"].iloc[-2]
    rsi_compra = df["RSI"].iloc[-1] < 30
    rsi_venda = df["RSI"].iloc[-1] > 70

    # Definir a quantidade fixa de BTC para cada operação
    quantidade_btc = 0.001  # Ajuste conforme necessário

    # 📌 Critério de COMPRA (ambos precisam ser atingidos)
    if cruzamento_compra and rsi_compra and ultima_ordem != "compra":
        print("\n🚀 Executando COMPRA...")
        comprar(quantidade_btc)

    # 📌 Critério de VENDA (qualquer um dos critérios pode ativar a venda)
    elif (cruzamento_venda or rsi_venda) and ultima_ordem != "venda":
        print("\n⚡ Executando VENDA...")
        vender(quantidade_btc)

    else:
        print("\n⏳ Nenhuma ação tomada. Aguardando nova oportunidade.\n")


# EXECUÇÃO
verificar_saldo()  # Mostra o saldo antes de qualquer ação
df = obter_dados_historicos(SYMBOL, TIMEFRAME, CANDLE_LIMIT)
df = calcular_indicadores(df)
obter_preco_atual(SYMBOL)
verificar_sinais(df)
executar_ordem(df)

import pandas as pd
import ta
from binance.client import Client
import time
import sys
import logging

# Configuração do sistema de logs
logging.basicConfig(
    filename="bot_trading.log",  # Nome do arquivo de log
    level=logging.INFO,  # Nível de registro
    format="%(asctime)s - %(levelname)s - %(message)s",  # Formato da mensagem
    datefmt="%Y-%m-%d %H:%M:%S",  # Formato da data
)

def registrar_log(mensagem):
    """ Registra uma mensagem no arquivo de log e exibe no terminal """
    logging.info(mensagem)  # Salva no arquivo de log
    print(mensagem)  # Exibe no terminal


# Configurar API Key e Secret Key (substituir pelos seus dados)
API_KEY = ""
API_SECRET = ""

# Criar cliente Binance
client = Client(API_KEY, API_SECRET)
#client = Client(API_KEY, API_SECRET, testnet=True)


# Configurações globais
SYMBOL = "BTCUSDT"  # Par de negociação
TIMEFRAME = Client.KLINE_INTERVAL_5MINUTE  # Timeframe de 5 minutos
CANDLE_LIMIT = 50  # Número de candles a buscar
STOP_LOSS_PERCENT = 5  # Vender se cair 5% abaixo do preço de compra
TAKE_PROFIT_PERCENT = 10  # Vender se subir 10% acima do preço de compra
MAX_USDT_POR_ORDEM = 10  # Valor máximo de USDT a ser usado por ordem de compra



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
    rsi_compra = ultimo_rsi < 35
    rsi_venda = ultimo_rsi > 65

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
    registrar_log(f"💰 Preço Atual do {symbol}: {preco_atual:.2f} USDT")
    return preco_atual

# Variável global para evitar ordens duplicadas
ultima_ordem = None

def verificar_saldo():
    """ Obtém os saldos disponíveis em USDT e BTC para negociação. """
    try:
        saldo_usdt = float(client.get_asset_balance(asset="USDT")["free"])
        saldo_btc = float(client.get_asset_balance(asset="BTC")["free"])
        
        mensagem = f"\n💰 Saldo Atual:\n  - USDT disponível: {saldo_usdt:.2f} USDT\n  - BTC disponível: {saldo_btc:.6f} BTC\n"
        registrar_log(mensagem)
        
        return saldo_usdt, saldo_btc
    except Exception as e:
        registrar_log(f"❌ Erro ao obter saldo: {e}")
        return 0, 0


def comprar():
    """ Executa uma ordem de compra de BTC respeitando o valor máximo por operação. """
    global ultima_ordem, preco_entrada
    try:
        saldo_usdt, saldo_btc = verificar_saldo()
        preco_atual = obter_preco_atual(SYMBOL)

        # Determinar a quantidade de BTC a comprar respeitando o limite de gasto
        qtd_btc = MAX_USDT_POR_ORDEM / preco_atual  # Divide o valor máximo pelo preço atual do BTC

        if saldo_usdt < MAX_USDT_POR_ORDEM:
            registrar_log("❌ Saldo insuficiente para compra!")
            return

        # Criar ordem de compra
        ordem = client.order_market_buy(symbol=SYMBOL, quantity=round(qtd_btc, 6))
        ultima_ordem = "compra"
        preco_entrada = preco_atual  # Salva o preço de entrada para monitoramento

        registrar_log(f"\n✅ COMPRA Executada! Quantidade: {qtd_btc:.6f} BTC por {preco_atual:.2f} USDT")
        registrar_log(f"💰 Valor gasto na compra: {MAX_USDT_POR_ORDEM:.2f} USDT\n")

        # Exibir saldo atualizado
        verificar_saldo()
    except Exception as e:
        registrar_log(f"❌ Erro ao executar COMPRA: {e}")



def vender():
    """ Executa uma ordem de venda de BTC com base no saldo disponível. """
    global ultima_ordem
    try:
        saldo_usdt, saldo_btc = verificar_saldo()
        preco_atual = obter_preco_atual(SYMBOL)

        if saldo_btc <= 0:
            registrar_log("❌ Saldo insuficiente para venda!")
            return

        # Criar ordem de venda com a quantidade total disponível
        ordem = client.order_market_sell(symbol=SYMBOL, quantity=round(saldo_btc, 6))
        ultima_ordem = "venda"

        # Cálculo do lucro ou prejuízo da operação
        lucro_prejuizo = (preco_atual - preco_entrada) * saldo_btc
        status_lucro = "🔼 Lucro" if lucro_prejuizo > 0 else "🔻 Prejuízo"

        registrar_log(f"\n✅ VENDA Executada! {saldo_btc:.6f} BTC vendidos a {preco_atual:.2f} USDT")
        registrar_log(f"{status_lucro}: {lucro_prejuizo:.2f} USDT\n")

        # Exibir saldo atualizado
        verificar_saldo()
    except Exception as e:
        registrar_log(f"❌ Erro ao executar VENDA: {e}")



def executar_ordem(df):
    """ Executa compra ou venda baseada nos sinais detectados e aplica Stop-Loss e Take-Profit """
    global ultima_ordem, preco_entrada

    # Últimos valores dos indicadores
    ultima_sma9 = df["SMA9"].iloc[-1]
    ultima_sma21 = df["SMA21"].iloc[-1]
    penultima_sma9 = df["SMA9"].iloc[-2]
    penultima_sma21 = df["SMA21"].iloc[-2]
    ultimo_rsi = df["RSI"].iloc[-1]

    # 📌 Recalcular os critérios dentro da função
    cruzamento_compra = ultima_sma9 > ultima_sma21 and penultima_sma9 <= penultima_sma21
    cruzamento_venda = ultima_sma9 < ultima_sma21 and penultima_sma9 >= penultima_sma21
    rsi_compra = ultimo_rsi < 35
    rsi_venda = ultimo_rsi > 65

    # Obter preço atual do ativo
    preco_atual = obter_preco_atual(SYMBOL)

    # 📌 Critério de COMPRA
    if cruzamento_compra and rsi_compra and ultima_ordem != "compra":
        registrar_log("\n🚀 Executando COMPRA...")
        comprar()

    # 📌 Critério de VENDA
    elif (cruzamento_venda or rsi_venda) and ultima_ordem != "venda":
        registrar_log("\n⚡ Executando VENDA por critério técnico...")
        vender()

    # 📌 Aplicar Stop-Loss e Take-Profit
    elif ultima_ordem == "compra":
        perda_maxima = preco_entrada * (1 - STOP_LOSS_PERCENT / 100)
        lucro_maximo = preco_entrada * (1 + TAKE_PROFIT_PERCENT / 100)

        if preco_atual <= perda_maxima:
            registrar_log(f"\n🚨 Stop-Loss atingido! Vendendo BTC a {preco_atual:.2f} USDT.")
            vender()

        elif preco_atual >= lucro_maximo:
            registrar_log(f"\n🏆 Take-Profit atingido! Vendendo BTC a {preco_atual:.2f} USDT.")
            vender()

    else:
        registrar_log("\n⏳ Nenhuma ação tomada. Aguardando nova oportunidade.\n")


def executar_bot():
    """ Loop infinito que executa o bot a cada minuto, com timer regressivo """
    while True:
        try:
            print("\n🔄 Executando novo ciclo de verificação...\n")

            # Verificar saldo antes de executar operações
            verificar_saldo()

            # Obter dados do mercado e calcular indicadores
            df = obter_dados_historicos(SYMBOL, TIMEFRAME, CANDLE_LIMIT)
            df = calcular_indicadores(df)

            # Exibir preço atual
            obter_preco_atual(SYMBOL)

            # Verificar sinais de compra e venda
            verificar_sinais(df)

            # Executar ordens de compra e venda conforme os critérios
            executar_ordem(df)

        except Exception as e:
            print(f"❌ Erro durante a execução do bot: {e}")

        # Timer regressivo de 60 segundos
        print("\n⏳ Aguardando para o próximo ciclo...\n")
        for i in range(60, 0, -1):
            sys.stdout.write(f"\r⌛ Próxima verificação em {i} segundos... ")
            sys.stdout.flush()
            time.sleep(1)
        
        print("\n")  # Nova linha para separar os ciclos

# Iniciar o loop do bot
executar_bot()

# EXECUÇÃO
verificar_saldo()  # Mostra o saldo antes de qualquer ação
df = obter_dados_historicos(SYMBOL, TIMEFRAME, CANDLE_LIMIT)
df = calcular_indicadores(df)
verificar_sinais(df)
executar_ordem(df)



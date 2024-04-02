from flask import Flask, render_template, request
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import requests
import io
import base64

app = Flask(__name__)

def fetch_cryptocurrency_data(crypto_id='bitcoin'):
    base_url = "https://api.coingecko.com/api/v3"
    chart_url = f"{base_url}/coins/{crypto_id}/market_chart?vs_currency=usd&days=1"
    response = requests.get(chart_url)
    data = response.json()
    # Check if 'prices' key exists in response data
    if 'prices' in data:
        return data['prices']
    else:
        return None

def preprocess_data(prices):
    if prices is None:
        return None
    df = pd.DataFrame(prices, columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df.dropna()
    return df

def calculate_moving_averages(df, windows=[1, 24]):
    if df is None:
        return None
    for window in windows:
        column_name = f'{window}h MA'
        df[column_name] = df['price'].rolling(f'{window}H').mean()
    return df

def calculate_rsi(df, periods=14):
    if df is None:
        return None
    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()

    RS = gain / loss
    RSI = 100 - (100 / (1 + RS))

    df['RSI'] = RSI
    return df

def create_plot(crypto_data):
    if not crypto_data:
        return None
    plt.figure(figsize=(12, 7))
    ax1 = plt.subplot(211)

    for crypto_id, df in crypto_data.items():
        if df is not None:
            ax1.plot(df.index, df['price'], label=f'{crypto_id} Price')
    ax1.set_title('Cryptocurrency Price Movement')
    ax1.set_ylabel('Price in USD')
    ax1.legend(loc='upper left')
    ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M'))
    plt.xticks(rotation=45)

    ax2 = plt.subplot(212, sharex=ax1)
    for crypto_id, df in crypto_data.items():
        if df is not None:
            ax2.plot(df.index, df['RSI'], label=f'{crypto_id} RSI')
    ax2.set_title('Relative Strength Index (RSI)')
    ax2.set_ylabel('RSI')
    ax2.axhline(70, linestyle='--', color='red')
    ax2.axhline(30, linestyle='--', color='green')
    ax2.legend(loc='upper left')

    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    graph_url = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    plt.close()
    return graph_url

@app.route('/', methods=['GET', 'POST'])
def home():
    crypto_ids = 'bitcoin,ethereum'  # Default cryptocurrencies
    error_message = None
    plot_url = None
    if request.method == 'POST':
        crypto_ids_input = request.form.get('crypto_ids', 'bitcoin,ethereum')
        crypto_ids = [cid.strip() for cid in crypto_ids_input.split(',')]

        crypto_data = {}
        for crypto_id in crypto_ids:
            prices = fetch_cryptocurrency_data(crypto_id)
            if prices is not None:
                df = preprocess_data(prices)
                df = calculate_moving_averages(df)
                df = calculate_rsi(df)
                crypto_data[crypto_id] = df
            else:
                error_message = f"Data for {crypto_id} could not be fetched."

        plot_url = create_plot(crypto_data)

    return render_template('index2.html', plot_url=plot_url, crypto_ids=', '.join(crypto_ids), error_message=error_message)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

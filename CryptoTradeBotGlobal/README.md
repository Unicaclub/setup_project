# 🚀 CryptoTradeBotGlobal

**Enterprise-Grade Cryptocurrency Trading System**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security: Bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)

A production-ready, multi-exchange cryptocurrency trading bot with advanced risk management, machine learning strategies, and enterprise-grade architecture.

## 🎯 Key Features

### 🏗️ **Enterprise Architecture**
- **Modular Design**: Clean separation of concerns with adapter pattern
- **Async/Await**: High-performance asynchronous operations
- **Event-Driven**: Real-time event bus for system communication
- **Microservices Ready**: Docker and Kubernetes deployment support
- **Scalable**: Horizontal scaling with Redis clustering

### 📈 **Advanced Trading Strategies**
- **Technical Analysis**: RSI, MACD, Bollinger Bands, Moving Averages
- **Mean Reversion**: Statistical arbitrage and pair trading
- **Trend Following**: Momentum-based strategies with confirmation
- **Breakout Trading**: Support/resistance level breakouts
- **Arbitrage**: Inter-exchange price difference exploitation
- **Machine Learning**: LSTM, Random Forest, XGBoost ensemble models

### 🛡️ **Enterprise Risk Management**
- **Portfolio Risk Controls**: Drawdown limits, position sizing, diversification
- **Real-time Monitoring**: VaR, CVaR, Sharpe ratio calculations
- **Circuit Breakers**: Automatic trading halt on excessive losses
- **Emergency Procedures**: Fail-safe mechanisms and recovery protocols
- **Compliance**: Audit trails and regulatory reporting

### 🔗 **Multi-Exchange Support**
- **Binance**: Spot and futures trading
- **Coinbase Pro**: Professional trading interface
- **Kraken**: European market access
- **OKX**: Global derivatives platform
- **Extensible**: Easy addition of new exchanges

### 🔐 **Security & Compliance**
- **API Key Encryption**: Military-grade encryption for credentials
- **Rate Limiting**: Exchange-specific rate limit management
- **Audit Logging**: Complete transaction and decision audit trail
- **Access Control**: Role-based permissions and authentication
- **Data Protection**: GDPR-compliant data handling

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- PostgreSQL 12+ (for production)
- Redis 6+ (for caching and pub/sub)
- Docker & Docker Compose (optional)

### Installation

1. **Clone the Repository**
```bash
git clone https://github.com/Unicaclub/setup_project.git
cd setup_project/CryptoTradeBotGlobal
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize Database**
```bash
python scripts/init_database.py
```

6. **Run the Bot**
```bash
python main.py
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Scale services
docker-compose up -d --scale trading-engine=3
```

## 📊 Configuration

### Environment Variables

The system uses environment variables for configuration. Copy `.env.example` to `.env` and configure:

```bash
# Trading Configuration
TRADING_MODE=paper  # paper, live, backtest
TRADING_BASE_CURRENCY=USDT
TRADING_MAX_POSITION_SIZE=1000.0

# Exchange API Keys (keep secure!)
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here

# Risk Management
TRADING_MAX_DAILY_LOSS=500.0
TRADING_MAX_DRAWDOWN=0.15
```

### Strategy Configuration

Strategies are configured in `config/strategies.yaml`:

```yaml
strategies:
  trend_following:
    enabled: true
    parameters:
      fast_ma_period: 12
      slow_ma_period: 26
      stop_loss_pct: 0.03
    risk_management:
      max_position_size: 1000.0
      risk_per_trade: 0.02
```

### Risk Management

Risk parameters are defined in `config/risk_management.yaml`:

```yaml
portfolio_risk:
  max_portfolio_risk: 0.10
  max_daily_loss: 0.05
  max_drawdown: 0.20
```

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Trading       │    │   Strategy      │    │   Risk          │
│   Engine        │◄──►│   Manager       │◄──►│   Manager       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Exchange      │    │   Data          │    │   Portfolio     │
│   Adapters      │    │   Manager       │    │   Manager       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Event Bus     │◄──►│   State         │◄──►│   Health        │
│                 │    │   Manager       │    │   Monitor       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Directory Structure

```
CryptoTradeBotGlobal/
├── src/
│   ├── core/                 # Core system components
│   │   ├── trading_engine.py # Main trading orchestration
│   │   ├── event_bus.py      # Event-driven communication
│   │   ├── state_manager.py  # System state management
│   │   └── health_monitor.py # System health monitoring
│   ├── adapters/             # Exchange adapters
│   │   └── exchanges/        # Exchange-specific implementations
│   ├── strategies/           # Trading strategies
│   │   ├── technical/        # Technical analysis strategies
│   │   ├── arbitrage/        # Arbitrage strategies
│   │   └── ml_strategies/    # Machine learning strategies
│   └── utils/                # Utility functions
├── config/                   # Configuration files
│   ├── settings.py          # Main configuration
│   ├── exchanges.yaml       # Exchange settings
│   ├── strategies.yaml      # Strategy parameters
│   └── risk_management.yaml # Risk management rules
├── tests/                   # Test suite
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── data/                    # Data storage
└── logs/                    # Log files
```

## 📈 Trading Strategies

### Technical Analysis Strategies

#### Trend Following
- **Moving Average Crossover**: EMA 12/26 with signal confirmation
- **MACD Strategy**: MACD line and signal line crossovers
- **Momentum Trading**: RSI and price momentum indicators

#### Mean Reversion
- **Bollinger Bands**: Price reversion to mean with volatility bands
- **RSI Oversold/Overbought**: Contrarian signals at extreme levels
- **Statistical Arbitrage**: Pair trading with correlation analysis

#### Breakout Trading
- **Support/Resistance Breakouts**: Level-based entry signals
- **Volume Confirmation**: High volume breakout validation
- **False Breakout Protection**: Multiple confirmation filters

### Machine Learning Strategies

#### LSTM Neural Networks
- **Price Prediction**: Time series forecasting with LSTM
- **Feature Engineering**: Technical indicators and market data
- **Ensemble Methods**: Multiple model combination

#### Random Forest & XGBoost
- **Classification Models**: Buy/sell/hold signal prediction
- **Feature Importance**: Automated feature selection
- **Cross-Validation**: Robust model validation

## 🛡️ Risk Management

### Portfolio Risk Controls

- **Position Sizing**: Kelly Criterion, fixed percentage, volatility-adjusted
- **Diversification**: Maximum correlation and concentration limits
- **Drawdown Protection**: Dynamic position reduction on losses
- **Stop Loss Management**: Trailing stops and profit taking

### Real-time Monitoring

- **Value at Risk (VaR)**: 95% confidence level risk measurement
- **Conditional VaR**: Expected shortfall calculation
- **Sharpe Ratio**: Risk-adjusted return monitoring
- **Maximum Drawdown**: Peak-to-trough loss tracking

### Emergency Procedures

- **Circuit Breakers**: Automatic trading halt on excessive losses
- **Emergency Shutdown**: Complete system shutdown capability
- **Position Liquidation**: Rapid position closure procedures
- **Manual Override**: Human intervention capabilities

## 🔧 Development

### Setting Up Development Environment

1. **Install Development Dependencies**
```bash
pip install -r requirements-dev.txt
```

2. **Install Pre-commit Hooks**
```bash
pre-commit install
```

3. **Run Tests**
```bash
pytest tests/ -v --cov=src/
```

4. **Code Formatting**
```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

### Adding New Exchanges

1. Create exchange adapter in `src/adapters/exchanges/`
2. Implement `BaseExchange` interface
3. Add configuration in `config/exchanges.yaml`
4. Add tests in `tests/adapters/exchanges/`

### Adding New Strategies

1. Create strategy class inheriting from `BaseStrategy`
2. Implement required methods: `analyze()`, `generate_signal()`, `calculate_risk()`
3. Add configuration in `config/strategies.yaml`
4. Add comprehensive tests

## 📊 Monitoring & Observability

### Metrics & Monitoring

- **Prometheus Metrics**: System and trading metrics
- **Grafana Dashboards**: Real-time visualization
- **Health Checks**: Endpoint monitoring
- **Performance Tracking**: Latency and throughput metrics

### Logging

- **Structured Logging**: JSON-formatted logs with context
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Audit Trail**: Complete trading decision logging
- **Log Rotation**: Automatic log file management

### Alerting

- **Email Alerts**: Critical system notifications
- **Slack Integration**: Team communication
- **Telegram Bot**: Mobile notifications
- **Webhook Support**: Custom alert endpoints

## 🚀 Deployment

### Production Deployment

#### Docker Deployment
```bash
# Build production image
docker build -t cryptobot:latest .

# Run with production configuration
docker run -d --name cryptobot \
  --env-file .env.production \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  cryptobot:latest
```

#### Kubernetes Deployment
```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Scale deployment
kubectl scale deployment cryptobot --replicas=3
```

### Environment-Specific Configurations

#### Development
- Paper trading enabled
- Debug logging
- Local database
- Reduced position sizes

#### Staging
- Paper trading with real data
- Production-like configuration
- Performance testing
- Integration testing

#### Production
- Live trading enabled
- Optimized performance
- High availability setup
- Comprehensive monitoring

## 🔐 Security

### API Key Management

- **Encryption**: AES-256 encryption for stored API keys
- **Environment Variables**: Secure configuration management
- **Key Rotation**: Automated API key rotation
- **Access Control**: Role-based access to sensitive operations

### Network Security

- **TLS/SSL**: Encrypted communication with exchanges
- **IP Whitelisting**: Restricted API access
- **Rate Limiting**: DDoS protection
- **Firewall Rules**: Network-level security

### Audit & Compliance

- **Transaction Logging**: Complete audit trail
- **Data Retention**: Configurable retention policies
- **Compliance Reporting**: Regulatory report generation
- **Access Logging**: User activity monitoring

## 📚 Documentation

### API Documentation

- **FastAPI Docs**: Auto-generated API documentation
- **OpenAPI Spec**: Machine-readable API specification
- **Postman Collection**: API testing collection

### User Guides

- **Getting Started**: Quick setup guide
- **Configuration**: Detailed configuration options
- **Strategy Development**: Custom strategy creation
- **Troubleshooting**: Common issues and solutions

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

### Code Standards

- **PEP 8**: Python code style guide
- **Type Hints**: Full type annotation
- **Docstrings**: Comprehensive documentation
- **Test Coverage**: Minimum 85% coverage

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**IMPORTANT**: This software is for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Always:

- Start with paper trading
- Never invest more than you can afford to lose
- Understand the risks involved
- Comply with local regulations
- Seek professional financial advice

## 🆘 Support

### Getting Help

- **Documentation**: Check our comprehensive docs
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Join our GitHub Discussions
- **Discord**: Join our community Discord server

### Professional Support

For enterprise support, custom development, or consulting services, contact us at:
- Email: support@cryptotradebotglobal.com
- Website: https://cryptotradebotglobal.com

## 🙏 Acknowledgments

- **CCXT Library**: Cryptocurrency exchange integration
- **TA-Lib**: Technical analysis indicators
- **FastAPI**: Modern web framework
- **PostgreSQL**: Reliable database system
- **Redis**: High-performance caching
- **Docker**: Containerization platform

---

**Built with ❤️ by the CryptoTradeBotGlobal Team**

*Making cryptocurrency trading accessible, safe, and profitable for everyone.*

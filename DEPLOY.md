# Деплой на Oracle Cloud Always Free

Як працює: на одному безкоштовному ARM-сервері запускаються ті самі контейнери, що й локально.
Caddy роздає фронтенд, проксує `/api/*` на бекенд і сам отримує HTTPS-сертифікат.

```
Інтернет ──► Caddy :80/:443 ──┬─► /         → frontend/ (статичні файли)
                              └─► /api/*    → backend:8000 ──► postgres, redis
                                                celery_worker ─┘
```

---

## 1. Акаунт і сервер

1. Зареєструйся на <https://www.oracle.com/cloud/free/>. Для перевірки знадобиться картка: знімуть і повернуть ~1 $.
   **Home region змінити потім не можна.** Якщо в регіоні не буде вільних ARM-серверів, доведеться чекати.
2. **Compute → Instances → Create instance**:
   - **Image:** Canonical Ubuntu 24.04
   - **Shape:** Ampere → `VM.Standard.A1.Flex`, 2 OCPU / 12 GB RAM (безкоштовно до 4 OCPU / 24 GB)
   - **Networking:** створи нову VCN з публічною підмережею, увімкни *Assign a public IPv4 address*
   - **SSH keys:** завантаж свій публічний ключ (`~/.ssh/id_ed25519.pub`; якщо його немає, створи командою `ssh-keygen -t ed25519`)
   - Якщо бачиш помилку *Out of capacity*, спробуй інший Availability Domain або повтори пізніше.
3. Запиши **Public IP** сервера.

## 2. Відкрити порти 80 і 443

**В Oracle:** Instance → Subnet → Security List → *Add Ingress Rules*. Додай два правила:

| Source CIDR | Protocol | Destination port |
|---|---|---|
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |

**На самому сервері** (в Ubuntu-образах Oracle вбудований фаєрвол блокує все, крім SSH):

```bash
ssh ubuntu@<PUBLIC_IP>
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

## 3. Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit          # перелогінься, щоб група docker застосувалась
ssh ubuntu@<PUBLIC_IP>
```

## 4. Безкоштовний домен (для HTTPS)

1. Зайди на <https://www.duckdns.org> (вхід через GitHub).
2. Створи субдомен, наприклад `mlgr`, і вкажи в полі *current ip* Public IP сервера.
3. Твій домен: `mlgr.duckdns.org`.

Без домену сайт теж працюватиме по `http://<PUBLIC_IP>`, але без HTTPS паролі передаються відкритим текстом.

## 5. Код і налаштування

```bash
git clone https://github.com/yujilong07/MLGR.git
cd MLGR
cp deploy/.env.example .env
openssl rand -hex 32   # двічі: для POSTGRES_PASSWORD і для SECRET_KEY
nano .env
```

Якщо репозиторій приватний, на сервері створи ключ (`ssh-keygen -t ed25519`), додай `~/.ssh/id_ed25519.pub`
у GitHub → репозиторій → Settings → Deploy keys і клонуй через `git@github.com:yujilong07/MLGR.git`.

Приклад `.env`:

```env
DOMAIN=mlgr.duckdns.org
POSTGRES_PASSWORD=<32 hex-символи>
SECRET_KEY=<інші 32 hex-символи>
GROQ_API_KEY=<ключ з console.groq.com>
```

## 6. Запуск

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps        # усі сервіси мають бути Up
docker compose -f docker-compose.prod.yml logs -f backend
```

Відкрий `https://mlgr.duckdns.org`. Першого разу сертифікат видається приблизно 10–30 секунд.

---

## Оновлення після змін у коді

```bash
cd ~/MLGR
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Міграції бази застосовуються автоматично під час старту бекенду (`alembic upgrade head`).

## Резервна копія бази

```bash
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres lab_report_db > backup_$(date +%F).sql
```

## Якщо щось не працює

| Симптом | Що перевірити |
|---|---|
| Сайт не відкривається взагалі | Правила Security List і `iptables` з кроку 2 |
| Помилка сертифіката | DuckDNS вказує на правильний IP; порт 80 відкритий (потрібен для Let's Encrypt) |
| `500` при реєстрації або вході | `docker compose -f docker-compose.prod.yml logs backend` |
| Документ «генерується» безкінечно | `docker compose -f docker-compose.prod.yml logs celery_worker` |

Oracle може вимкнути Always Free сервер, який тиждень майже не навантажений.
Якщо це станеться, просто запусти інстанс знову в консолі: дані на диску зберігаються.

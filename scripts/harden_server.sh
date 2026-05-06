#!/usr/bin/env bash
# =============================================================================
# Скрипт hardened-настройки сервера для AI Tutor Project
# Server Hardening Script — GPU-vendor agnostic
# =============================================================================
# Использование:
#   sudo ./harden_server.sh              # Полная настройка
#   sudo ./harden_server.sh --skip-ssh   # Пропустить настройку SSH
#   sudo ./harden_server.sh --help       # Помощь
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Цветной вывод / Colored output
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }
step()    { echo -e "\n${CYAN}${BOLD}==> $*${NC}"; }

# ---------------------------------------------------------------------------
# Парсинг аргументов / Argument parsing
# ---------------------------------------------------------------------------
SKIP_SSH=false
SKIP_FAIL2BAN=false
DRY_RUN=false

show_help() {
    cat <<'EOF'
Использование / Usage:
  sudo ./harden_server.sh [OPTIONS]

Опции / Options:
  --skip-ssh        Пропустить настройку SSH
  --skip-fail2ban   Пропустить настройку fail2ban
  --dry-run         Показать действия без выполнения
  --help            Показать эту справку

Описание:
  Настраивает безопасность Ubuntu Server 22.04 LTS:
  - Обновление пакетов
  - Настройка UFW (файрвол)
  - Настройка SSH (отключение root, ключи, порт 2222)
  - Настройка fail2ban
  - Автоматические обновления безопасности
  - Настройка sysctl (сеть)
  - Отключение ненужных служб
  - Настройка ротации логов
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-ssh)      SKIP_SSH=true; shift ;;
        --skip-fail2ban) SKIP_FAIL2BAN=true; shift ;;
        --dry-run)       DRY_RUN=true; shift ;;
        --help|-h)       show_help ;;
        *) error "Неизвестный параметр: $1"; echo "Используйте --help для справки"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Проверки / Pre-flight checks
# ---------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    error "Скрипт должен запускаться от root (sudo)."
    exit 1
fi

if ! grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
    warn "ОС не Ubuntu. Скрипт тестировался на Ubuntu 22.04 LTS."
fi

# Вспомогательная функция: безопасное копирование с резервной копией
backup_file() {
    local target="$1"
    if [[ -f "$target" ]]; then
        local backup="${target}.bak.$(date +%Y%m%d%H%M%S)"
        cp "$target" "$backup"
        info "Резервная копия: $backup"
    fi
}

# Выполнение с проверкой dry-run
run_cmd() {
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} $*"
    else
        eval "$@"
    fi
}

# Количество шагов
TOTAL_STEPS=8
STEP_NUM=0

# =============================================================================
step "1/${TOTAL_STEPS}: Обновление пакетов / Updating system packages"
# =============================================================================
STEP_NUM=$((STEP_NUM + 1))

run_cmd "export DEBIAN_FRONTEND=noninteractive"
run_cmd "apt-get update -qq"
run_cmd "apt-get upgrade -y -qq -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold'"
run_cmd "apt-get dist-upgrade -y -qq -o Dpkg::Options::='--force-confdef' -o Dpkg::Options::='--force-confold'"
success "Пакеты обновлены"

# =============================================================================
step "2/${TOTAL_STEPS}: Настройка UFW / Configuring firewall"
# =============================================================================
STEP_NUM=$((STEP_NUM + 1))

# Установка UFW если нет
if ! command -v ufw &>/dev/null; then
    run_cmd "apt-get install -y -qq ufw"
fi

# Сброс существующих правил (idempotent)
run_cmd "ufw --force reset"

# Правила по умолчанию
run_cmd "ufw default deny incoming"
run_cmd "ufw default allow outgoing"

# Разрешённые порты
run_cmd "ufw allow 2222/tcp comment 'SSH (custom port)'"
run_cmd "ufw allow 80/tcp comment 'HTTP'"
run_cmd "ufw allow 443/tcp comment 'HTTPS'"
run_cmd "ufw allow 8000/tcp comment 'FastAPI application'"

# Redis — только локально
run_cmd "ufw allow in on lo to any port 6379 proto tcp comment 'Redis local only'"

# Включить UFW
run_cmd "ufw --force enable"
success "UFW настроен: SSH(2222), HTTP(80), HTTPS(443), API(8000), Redis(local only)"

# =============================================================================
step "3/${TOTAL_STEPS}: Настройка SSH / Hardening SSH"
# =============================================================================
STEP_NUM=$((STEP_NUM + 1))

SSHD_CONFIG="/etc/ssh/sshd_config"
SSHD_CONFIG_D="/etc/ssh/sshd_config.d/99-hardened.conf"

if [[ "$SKIP_SSH" == false ]]; then
    backup_file "$SSHD_CONFIG"

    # Проверяем, существует ли директория sshd_config.d
    mkdir -p /etc/ssh/sshd_config.d

    # Создаём drop-in конфигурацию (не трогаем основной файл)
    cat > "$SSHD_CONFIG_D" <<'SSHD_EOF'
# ===== AI Tutor — SSH Hardening =====
# Сгенерировано скриптом harden_server.sh

# Порт SSH
Port 2222

# Запрет входа root
PermitRootLogin no

# Только ключи (без паролей)
PubkeyAuthentication yes
PasswordAuthentication no
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
UsePAM no

# Ограничения
MaxAuthTries 3
MaxSessions 5
LoginGraceTime 30

# Безопасность
X11Forwarding no
AllowTcpForwarding no
PermitEmptyPasswords no
HostbasedAuthentication no

# Таймауты
ClientAliveInterval 300
ClientAliveCountMax 2

# Логирование
LogLevel VERBOSE
SSHD_EOF

    chmod 600 "$SSHD_CONFIG_D"
    info "Конфигурация SSH: $SSHD_CONFIG_D"

    # Проверяем валидность конфигурации
    if sshd -t 2>/dev/null; then
        run_cmd "systemctl restart sshd || systemctl restart ssh"
        success "SSH перезапущен (порт 2222, ключи только)"
    else
        error "Ошибка в конфигурации SSH! Откатываем изменения."
        rm -f "$SSHD_CONFIG_D"
        error "Ручная настройка SSH требуется."
    fi

    warn "ВАЖНО: Убедитесь что ваш SSH ключ добавлен ДО закрытия текущей сессии!"
    warn "Новое подключение: ssh -p 2222 user@hostname"
else
    info "Настройка SSH пропущена (--skip-ssh)"
fi

# =============================================================================
step "4/${TOTAL_STEPS}: Настройка fail2ban / Configuring fail2ban"
# =============================================================================
STEP_NUM=$((STEP_NUM + 1))

if [[ "$SKIP_FAIL2BAN" == false ]]; then
    # Установка
    if ! command -v fail2ban-client &>/dev/null; then
        run_cmd "apt-get install -y -qq fail2ban"
    fi

    # Создаём локальную конфигурацию (не трогаем jail.conf)
    F2B_LOCAL="/etc/fail2ban/jail.local"
    backup_file "$F2B_LOCAL"

    cat > "$F2B_LOCAL" <<'F2B_EOF'
# ===== AI Tutor — fail2ban configuration =====

[DEFAULT]
# Бан на 1 час, максимум 3 попытки
bantime  = 3600
findtime = 600
maxretry = 3
# Используем UFW вместо iptables
banaction = ufw
action = %(action_mwl)s

[sshd]
enabled  = true
port     = 2222
filter   = sshd
logpath  = /var/log/auth.log
maxretry = 3
bantime  = 3600
findtime = 600

# Защита от брутфорса API
[api-auth]
enabled  = true
port     = http,https,8000
filter   = custom-api-auth
logpath  = /var/log/ai-tutor/api.log
maxretry = 10
bantime  = 1800
findtime = 300
F2B_EOF

    # Создаём фильтр для API (если есть)
    mkdir -p /etc/fail2ban/filter.d
    cat > /etc/fail2ban/filter.d/custom-api-auth.conf <<'FILTER_EOF'
[Definition]
failregex = ^.*"POST /api/v1/.*" (401|403) .*$
ignoreregex =
FILTER_EOF

    run_cmd "systemctl enable fail2ban"
    run_cmd "systemctl restart fail2ban"
    success "fail2ban настроен и запущен"
else
    info "Настройка fail2ban пропущена (--skip-fail2ban)"
fi

# =============================================================================
step "5/${TOTAL_STEPS}: Автоматические обновления / Automatic security updates"
# =============================================================================
STEP_NUM=$((STEP_NUM + 1))

run_cmd "apt-get install -y -qq unattended-upgrades apt-listchanges"

backup_file "/etc/apt/apt.conf.d/50unattended-upgrades"
backup_file "/etc/apt/apt.conf.d/20auto-upgrades"

cat > /etc/apt/apt.conf.d/50unattended-upgrades <<'UPGRADES_EOF'
// ===== AI Tutor — Automatic Security Updates =====
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Mail "root";
UPGRADES_EOF

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'AUTO_EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
AUTO_EOF

run_cmd "systemctl enable unattended-upgrades"
success "Автоматические обновления безопасности включены"

# =============================================================================
step "6/${TOTAL_STEPS}: Настройка sysctl / Network security kernel params"
# =============================================================================
STEP_NUM=$((STEP_NUM + 1))

SYSCTL_FILE="/etc/sysctl.d/99-ai-tutor-security.conf"
backup_file "$SYSCTL_FILE"

cat > "$SYSCTL_FILE" <<'SYSCTL_EOF'
# ===== AI Tutor — Sysctl Security Hardening =====

# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.tcp_synack_retries = 2

# Reverse path filtering (anti-spoofing)
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Disable IP source routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# Disable ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0

# Enable execshield / ASLR
kernel.randomize_va_space = 2

# Log martian packets
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# Ignore ICMP broadcasts
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Ignore bogus ICMP errors
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Connection tracking
net.netfilter.nf_conntrack_max = 131072

# File descriptors
fs.file-max = 2097152
fs.nr_open = 1048576

# Shared memory (для больших моделей)
kernel.shmmax = 1073741824
kernel.shmall = 262144

# Disable IPv6 если не нужен (раскомментировать при необходимости)
# net.ipv6.conf.all.disable_ipv6 = 1
# net.ipv6.conf.default.disable_ipv6 = 1
SYSCTL_EOF

run_cmd "sysctl --system > /dev/null 2>&1"
success "Настройки sysctl применены"

# =============================================================================
step "7/${TOTAL_STEPS}: Отключение ненужных служб / Disable unused services"
# =============================================================================
STEP_NUM=$((STEP_NUM + 1))

DISABLED_SERVICES="cups cups-browsed avahi-daemon avahi-daemon.socket whoopsie snapd snapd.socket apport"

for svc in $DISABLED_SERVICES; do
    if systemctl is-enabled "$svc" &>/dev/null; then
        run_cmd "systemctl stop $svc 2>/dev/null || true"
        run_cmd "systemctl disable $svc 2>/dev/null || true"
        info "Отключена служба: $svc"
    fi
done

# Отключаем графические цели (если вдруг есть)
run_cmd "systemctl set-default multi-user.target 2>/dev/null || true"

success "Ненужные службы отключены"

# =============================================================================
step "8/${TOTAL_STEPS}: Ротация логов приложения / Application log rotation"
# =============================================================================
STEP_NUM=$((STEP_NUM + 1))

mkdir -p /var/log/ai-tutor
run_cmd "chown root:adm /var/log/ai-tutor"

cat > /etc/logrotate.d/ai-tutor <<'LOGROTATE_EOF'
# ===== AI Tutor — Application Log Rotation =====
/var/log/ai-tutor/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 root adm
    sharedscripts
    postrotate
        docker compose -f <PROJECT_ROOT>/docker-compose.yml logs --tail=0 > /dev/null 2>&1 || true
    endscript
}

/var/log/ai-tutor/*.json {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 root adm
}
LOGROTATE_EOF

run_cmd "logrotate --force /etc/logrotate.d/ai-tutor 2>/dev/null || true"
success "Ротация логов настроена (/etc/logrotate.d/ai-tutor)"

# =============================================================================
# Итоговое резюме / Summary
# =============================================================================
echo ""
echo -e "${GREEN}${BOLD}========================================${NC}"
echo -e "${GREEN}${BOLD}  Настройка безопасности завершена!      ${NC}"
echo -e "${GREEN}${BOLD}  Security hardening complete!           ${NC}"
echo -e "${GREEN}${BOLD}========================================${NC}"
echo ""
info "Сводка настроек:"
echo "  🔥 UFW:       SSH(2222), HTTP(80), HTTPS(443), API(8000), Redis(local)"
echo "  🔑 SSH:       Порт 2222, ключи, root отключён"
if [[ "$SKIP_FAIL2BAN" == false ]]; then
    echo "  🛡️  fail2ban:  Включён (3 попытки → бан 1ч)"
fi
echo "  📦 Обновления: Автоматические (security only)"
echo "  ⚙️  sysctl:    SYN cookies, RP filter, ASLR"
echo "  🚫 Службы:    cups, avahi, snapd отключены"
echo "  📋 Логи:      Ротация 30 дней"
echo ""
warn "ПОМНИТЕ: Подключаться теперь через порт 2222!"
warn "  ssh -p 2222 user@hostname"
echo ""

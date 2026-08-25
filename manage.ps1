<#
.SYNOPSIS
    اسکریپت مدیریت و راه‌اندازی آسان پروژه Sign Scanner Pro

.DESCRIPTION
    بررسی خودکار پایتون، ساخت/فعال‌سازی محیط مجازی (venv)، نصب وابستگی‌ها،
    ساخت پوشه‌های لازم و اجرای برنامه یا دستورات دیگر با منوی تعاملی و آرگومان‌ها.

.EXAMPLE
    .\manage.ps1
    .\manage.ps1 run
    .\manage.ps1 install
    .\manage.ps1 clean
#>

param (
    [Parameter(Position = 0)]
    [ValidateSet("start", "run", "install", "setup", "clean", "help", "menu")]
    [string]$Action = "start",

    [Parameter()]
    [int]$Port = 8080,

    [Parameter()]
    [switch]$NoBrowser
)

$Host.UI.RawUI.WindowTitle = "Sign Scanner Pro - Management"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Header {
    Clear-Host
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   سامانه هوشمند تولید برگه و استخراج امضا (Sign Scanner Pro)   " -ForegroundColor Yellow -BackgroundColor Black
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Check-Python {
    Write-Host "🔍 در حال بررسی مفسر پایتون..." -ForegroundColor DarkGray
    $pyCmd = $null

    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        $pyCmd = "python"
    } elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
        $pyCmd = "py"
    }

    if (-not $pyCmd) {
        Write-Host "❌ خطا: پایتون در سیستم شما یافت نشد!" -ForegroundColor Red
        Write-Host "لطفاً ابتدا پایتون ۳.۹ یا بالاتر را از python.org نصب کنید و تیک Add to PATH را بزنید." -ForegroundColor Yellow
        exit 1
    }

    $pyVer = & $pyCmd --version 2>&1
    Write-Host "✔ پایتون یافت شد: $pyVer" -ForegroundColor Green
    return $pyCmd
}

function Ensure-Directories {
    $dirs = @("scans", "output\signatures", "data")
    foreach ($d in $dirs) {
        if (-not (Test-Path $d)) {
            New-Item -ItemType Directory -Path $d -Force | Out-Null
            Write-Host "📁 پوشه $d ایجاد شد." -ForegroundColor DarkGray
        }
    }
}

function Setup-Venv {
    param ([string]$pyCmd)
    
    $venvDir = ".venv"
    $venvPython = "$venvDir\Scripts\python.exe"

    if (-not (Test-Path $venvPython)) {
        Write-Host "⚙️ در حال ساخت محیط مجازی (venv)..." -ForegroundColor Yellow
        & $pyCmd -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ ساخت venv با خطا مواجه شد. از پایتون سیستم استفاده می‌شود." -ForegroundColor DarkYellow
            return $pyCmd
        }
        Write-Host "✔ محیط مجازی با موفقیت ایجاد شد." -ForegroundColor Green
    }

    return $venvPython
}

function Install-Dependencies {
    param ([string]$pyExecutable)
    
    Write-Host "📦 در حال به‌روزرسانی pip و نصب وابستگی‌ها..." -ForegroundColor Cyan
    & $pyExecutable -m pip install --upgrade pip --quiet
    & $pyExecutable -m pip install -r requirements.txt
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✔ تمامی پیش‌نیازها با موفقیت نصب شدند." -ForegroundColor Green
    } else {
        Write-Host "⚠️ برخی پیش‌نیازها با خطا مواجه شدند. لطفاً اتصال اینترنت خود را بررسی کنید." -ForegroundColor Red
    }
}

function Start-App {
    param (
        [string]$pyExecutable,
        [int]$p,
        [bool]$noB
    )

    Ensure-Directories
    Write-Host ""
    Write-Host "🚀 در حال راه‌اندازی سرور برنامه روی پورت $p..." -ForegroundColor Green
    Write-Host "🌐 آدرس پنل وب: http://localhost:$p" -ForegroundColor Cyan
    Write-Host "برای خروج یا توقف، کلید Ctrl+C را فشار دهید." -ForegroundColor DarkGray
    Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host ""

    $argsList = @("main.py", "--port", $p)
    if ($noB) {
        $argsList += "--no-browser"
    }

    & $pyExecutable $argsList
}

function Clean-Project {
    Write-Host "🧹 در حال پاکسازی فایل‌های موقت..." -ForegroundColor Yellow
    Get-ChildItem -Path . -Include "__pycache__", "*.pyc", "*.pyo" -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✔ فایل‌های موقت و کش پاکسازی شدند." -ForegroundColor Green
}

function Show-InteractiveMenu {
    param ([string]$pyExecutable)

    while ($true) {
        Write-Header
        Write-Host "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:" -ForegroundColor White
        Write-Host " [1] 🚀 اجرای برنامه (Start Web App)" -ForegroundColor Green
        Write-Host " [2] 📦 نصب / ارتقای مجدد وابستگی‌ها (Install Requirements)" -ForegroundColor Yellow
        Write-Host " [3] 🧹 پاکسازی کش و فایل‌های موقت (Clean Cache)" -ForegroundColor Cyan
        Write-Host " [4] 📁 باز کردن پوشه‌های خروجی (Open Output Folders)" -ForegroundColor Magenta
        Write-Host " [0] ❌ خروج (Exit)" -ForegroundColor Red
        Write-Host ""
        
        $choice = Read-Host "گزینه انتخابی [پیش‌فرض 1]"
        if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "1" }

        switch ($choice) {
            "1" {
                Start-App -pyExecutable $pyExecutable -p $Port -noB $NoBrowser
                break
            }
            "2" {
                Install-Dependencies -pyExecutable $pyExecutable
                Write-Host "`nبرای ادامه کلیدی را فشار دهید..." -ForegroundColor DarkGray
                [Console]::ReadKey($true) | Out-Null
            }
            "3" {
                Clean-Project
                Write-Host "`nبرای ادامه کلیدی را فشار دهید..." -ForegroundColor DarkGray
                [Console]::ReadKey($true) | Out-Null
            }
            "4" {
                Ensure-Directories
                Start-Process "explorer.exe" "output"
            }
            "0" {
                Write-Host "خداحافظ!" -ForegroundColor Cyan
                exit 0
            }
            default {
                Write-Host "گزینه نامعتبر است!" -ForegroundColor Red
                Start-Sleep -Seconds 1
            }
        }
    }
}

# اجرای بدنه اصلی
Write-Header
$pyCmd = Check-Python
$pyExec = Setup-Venv -pyCmd $pyCmd

# بررسی نیاز به نصب پکیج‌ها در صورت وجود نداشتن پکیج‌های اصلی
$testImport = & $pyExec -c "import reportlab, cv2, PIL" 2>&1
if ($LASTEXITCODE -ne 0 -and $Action -ne "clean") {
    Write-Host "⚡ اولین اجرای برنامه یا پیش‌نیازها کامل نیستند؛ در حال نصب خودکار وابستگی‌ها..." -ForegroundColor Yellow
    Install-Dependencies -pyExecutable $pyExec
}

switch ($Action.ToLower()) {
    "start" {
        Start-App -pyExecutable $pyExec -p $Port -noB $NoBrowser
    }
    "run" {
        Start-App -pyExecutable $pyExec -p $Port -noB $NoBrowser
    }
    "install" {
        Install-Dependencies -pyExecutable $pyExec
    }
    "setup" {
        Install-Dependencies -pyExecutable $pyExec
    }
    "clean" {
        Clean-Project
    }
    "menu" {
        Show-InteractiveMenu -pyExecutable $pyExec
    }
    "help" {
        Write-Host "راهنمای دستورات manage.ps1:" -ForegroundColor Yellow
        Write-Host "  .\manage.ps1              اجرای مستقیم و سریع برنامه"
        Write-Host "  .\manage.ps1 menu         نمایش منوی تعاملی کامل"
        Write-Host "  .\manage.ps1 install      نصب وابستگی‌ها در venv"
        Write-Host "  .\manage.ps1 clean        پاک کردن کش‌های پایتون"
        Write-Host "  .\manage.ps1 -Port 8081   اجرا روی پورت دلخواه"
    }
}

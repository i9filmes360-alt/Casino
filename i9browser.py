#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assistir — o navegador do YouDown, SEPARADO do downloader.

É exatamente o mesmo navegador do YouDown (abas, histórico, favoritos, autocompletar, AdBlock, Modo Estrito
do Redecanais, tela cheia do player...), sem a parte de download, com uma barra de BOTÕES DE SITES:

  • Digite um endereço na barra (ex.: redecanais.by) e tecle Enter: o site vira um BOTÃO.
  • Clique com o botão DIREITO num botão (ou use ⋮ → Editar botões) para editar nome/endereço ou apagar.
    Útil quando o site muda de endereço.

Requisitos (Windows 10/11): Python 3.9+ e   pip install tkwry     (usa o Microsoft Edge WebView2).
"""
import os
import re
import json
import sys
import time
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

# Auto-recuperação da dependência ao executar via código-fonte .py
if not getattr(sys, "frozen", False):
    try:
        __import__("tkwry")
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "tkwry"])
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Caminhos base
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Registro permanente de erros e falhas críticas (Crash Logger)
# ---------------------------------------------------------------------------
_app_instancia = None


def registrar_falha_fatal(exctype, value, tb):
    import traceback
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tb_str = "".join(traceback.format_exception(exctype, value, tb))
    msg_crash = (
        f"\n{'=' * 70}\n"
        f"FALHA CRÍTICA DO SISTEMA - {timestamp}\n"
        f"Tipo: {getattr(exctype, '__name__', str(exctype))}\n"
        f"Mensagem: {value}\n"
        f"Rastreamento (Traceback):\n{tb_str}"
        f"{'=' * 70}\n"
    )
    pastas_log = [
        os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv and sys.argv[0] else sys.executable)),
        os.path.join(os.path.expanduser("~"), ".youdown"),
        os.path.expanduser("~"),
    ]
    for p in pastas_log:
        try:
            os.makedirs(p, exist_ok=True)
            with open(os.path.join(p, "assistir_crash.log"), "a", encoding="utf-8") as f:
                f.write(msg_crash)
            break
        except Exception:
            continue
    try:
        if _app_instancia and hasattr(_app_instancia, "log"):
            _app_instancia.log(f"❌ [Falha Crítica] {value}", "erro")
    except Exception:
        pass
    try:
        sys.stderr.write(msg_crash)
        sys.stderr.flush()
    except Exception:
        pass


sys.excepthook = registrar_falha_fatal
if hasattr(threading, "excepthook"):
    threading.excepthook = lambda args: registrar_falha_fatal(args.exc_type, args.exc_value, args.exc_traceback)


class ArduinoTheme:
    TEAL = "#008184"
    TEAL_DARK = "#005c5e"
    TEAL_LIGHT = "#00a3a6"
    TEAL_HOVER = "#00a3a6"

    BG_TOOLBAR = "#008184"
    BG_STATUSBAR = "#008184"
    BG_SIDEBAR = "#f4f4f4"
    BG_EDITOR = "#ffffff"
    BG_OUTPUT = "#1a1a1a"

    FG_SIDEBAR = "#5c5c5c"
    FG_EDITOR = "#2d2d2d"
    FG_OUTPUT = "#d4d4d4"
    FG_STATUS = "#ffffff"

    BORDER = "#d0d0d0"
    BORDER_DARK = "#b0b0b0"

    TOOLTIP_BG = "#2d2d30"
    TOOLTIP_FG = "#ffffff"
    TOOLTIP_BORDER = "#3e3e42"

    SUCCESS = "#4ec9b0"
    ERROR = "#f48771"
    WARNING = "#dcdcaa"

    BG_NEUTRO = "#e0e0e0"
    NEUTRO_HOVER = "#d0d0d0"
    NEUTRO_PRESS = "#c0c0c0"
    DESABILITADO_BG = "#c0c0c0"
    DESABILITADO_FG = "#808080"
    TEAL_TEXTO = "#008184"
    TEXTO_ESPERA = "#666"
    PERIGO_TEXTO = "#c62828"

    TEMAS = {
        "claro": dict(
            BG_SIDEBAR="#f4f4f4",
            BG_EDITOR="#ffffff",
            BG_OUTPUT="#1a1a1a",
            FG_SIDEBAR="#5c5c5c",
            FG_EDITOR="#2d2d2d",
            BORDER="#d0d0d0",
            BORDER_DARK="#b0b0b0",
            BG_NEUTRO="#e0e0e0",
            NEUTRO_HOVER="#d0d0d0",
            NEUTRO_PRESS="#c0c0c0",
            DESABILITADO_BG="#c0c0c0",
            DESABILITADO_FG="#808080",
            TEAL_TEXTO="#008184",
            TEXTO_ESPERA="#666",
            PERIGO_TEXTO="#c62828",
        ),
        "escuro": dict(
            BG_SIDEBAR="#1e1e1e",
            BG_EDITOR="#2b2b2b",
            BG_OUTPUT="#121212",
            FG_SIDEBAR="#a8a8a8",
            FG_EDITOR="#e6e6e6",
            BORDER="#3c3c3c",
            BORDER_DARK="#555555",
            BG_NEUTRO="#3a3a3a",
            NEUTRO_HOVER="#4a4a4a",
            NEUTRO_PRESS="#5a5a5a",
            DESABILITADO_BG="#333333",
            DESABILITADO_FG="#777777",
            TEAL_TEXTO="#26c6c9",
            TEXTO_ESPERA="#9a9a9a",
            PERIGO_TEXTO="#ef5350",
        ),
    }

    @classmethod
    def aplicar(cls, nome):
        for chave, valor in cls.TEMAS[nome].items():
            setattr(cls, chave, valor)


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def limpar_ansi(s):
    return _ANSI_RE.sub("", s or "")


# ---------------------------------------------------------------------------
# Widgets customizados
# ---------------------------------------------------------------------------
class ToolTip:
    def __init__(self, widget, text="", delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip_window = None
        self._after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _show(self):
        if self._tip_window or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() - 90
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        except Exception:
            return
        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        border = tk.Frame(tw, bg=ArduinoTheme.TOOLTIP_BORDER, bd=0)
        border.pack(fill=tk.BOTH, expand=True)
        lbl = tk.Label(
            border, text=self.text,
            bg=ArduinoTheme.TOOLTIP_BG,
            fg=ArduinoTheme.TOOLTIP_FG,
            font=("Segoe UI", 9),
            padx=10, pady=5, justify=tk.LEFT,
        )
        lbl.pack(padx=1, pady=1)

    def _hide(self):
        if self._tip_window:
            try:
                self._tip_window.destroy()
            except Exception:
                pass
            self._tip_window = None


class EntryArduino(tk.Frame):
    def __init__(self, master, font, **kwargs):
        super().__init__(master, bg=ArduinoTheme.BORDER_DARK, **kwargs)
        self.inner = tk.Frame(self, bg=ArduinoTheme.BG_EDITOR)
        self.inner.pack(fill="both", expand=True, padx=2, pady=2)
        self.entry = tk.Entry(
            self.inner, font=font,
            bg="white", fg=ArduinoTheme.FG_EDITOR,
            insertbackground=ArduinoTheme.FG_EDITOR,
            relief="flat", bd=0, highlightthickness=0,
        )
        self.entry.pack(fill="both", expand=True, padx=5, pady=4)
        self.entry.bind("<Button-1>", lambda e: self.entry.focus_force(), add="+")
        self.entry.bind("<FocusIn>", lambda e: self._set_focus(True))
        self.entry.bind("<FocusOut>", lambda e: self._set_focus(False))

    def _set_focus(self, ativo):
        cor = ArduinoTheme.TEAL if ativo else ArduinoTheme.BORDER_DARK
        self.configure(bg=cor)

    def get(self):
        return self.entry.get()

    def insert(self, i, s):
        self.entry.insert(i, s)

    def delete(self, a, b):
        self.entry.delete(a, b)


class BotaoArduino(tk.Frame):
    def __init__(self, master, texto, comando, tipo="primary",
                 fonte=("Segoe UI", 9, "bold"), padx=10, pady=8):
        super().__init__(master, bg=master.cget("bg"))
        self.comando = comando
        self.ativo = True
        self.tipo = tipo
        self.cores = self._get_cores(tipo)

        self.corpo = tk.Label(
            self, text=texto, font=fonte,
            bg=self.cores["bg"], fg=self.cores["fg"],
            padx=padx, pady=pady,
            cursor="hand2",
            highlightthickness=1,
            highlightbackground=self.cores["border"],
            highlightcolor=self.cores["border"],
        )
        self.corpo.pack(fill="both", expand=True)

        self.corpo.bind("<Enter>", self._on_enter)
        self.corpo.bind("<Leave>", self._on_leave)
        self.corpo.bind("<Button-1>", self._on_press)
        self.corpo.bind("<ButtonRelease-1>", self._on_release)

    def _get_cores(self, tipo):
        if tipo == "secondary":
            return {
                "bg": ArduinoTheme.BG_NEUTRO,
                "fg": ArduinoTheme.FG_EDITOR,
                "border": ArduinoTheme.BORDER_DARK,
                "hover": ArduinoTheme.NEUTRO_HOVER,
                "press": ArduinoTheme.NEUTRO_PRESS,
            }
        if tipo == "success":
            return {
                "bg": "#2e7d32", "fg": "white", "border": "#1b5e20",
                "hover": "#388e3c", "press": "#1b5e20",
            }
        if tipo == "danger":
            return {
                "bg": "#c62828", "fg": "white", "border": "#8e0000",
                "hover": "#e53935", "press": "#8e0000",
            }
        if tipo == "warning":
            return {
                "bg": "#f57c00", "fg": "white", "border": "#b85c00",
                "hover": "#fb8c00", "press": "#b85c00",
            }
        return {
            "bg": ArduinoTheme.TEAL, "fg": "white",
            "border": ArduinoTheme.TEAL_DARK,
            "hover": ArduinoTheme.TEAL_HOVER,
            "press": ArduinoTheme.TEAL_DARK,
        }

    def _on_enter(self, _):
        if self.ativo:
            self.corpo.configure(bg=self.cores["hover"])

    def _on_leave(self, _):
        if self.ativo:
            self.corpo.configure(bg=self.cores["bg"])

    def _on_press(self, _):
        if self.ativo:
            self.corpo.configure(bg=self.cores["press"])

    def _on_release(self, _):
        if self.ativo:
            self.corpo.configure(bg=self.cores["hover"])
            if self.comando:
                self.comando()

    def set_estado(self, ativo, texto=None):
        self.ativo = ativo
        if texto is not None:
            self.corpo.configure(text=texto)
        if ativo:
            self.corpo.configure(
                bg=self.cores["bg"], fg=self.cores["fg"],
                cursor="hand2",
            )
        else:
            self.corpo.configure(
                bg=ArduinoTheme.DESABILITADO_BG,
                fg=ArduinoTheme.DESABILITADO_FG,
                cursor="arrow",
            )

    def aplicar_tema(self):
        self.cores = self._get_cores(self.tipo)
        self.corpo.configure(
            highlightbackground=self.cores["border"],
            highlightcolor=self.cores["border"],
        )
        self.set_estado(self.ativo)


class BarraProgressoArduino(tk.Frame):
    def __init__(self, master, altura=22):
        super().__init__(master, bg=master.cget("bg"))
        self.altura = altura
        self.valor = 0

        self.moldura = tk.Frame(
            self, bg=ArduinoTheme.BORDER_DARK,
            highlightthickness=0,
        )
        self.moldura.pack(fill="both", expand=True)

        self.trilho = tk.Frame(self.moldura, bg="#e0e0e0", height=altura)
        self.trilho.pack(fill="both", expand=True, padx=2, pady=2)
        self.trilho.pack_propagate(False)

        self.canvas = tk.Canvas(
            self.trilho, bg="#e0e0e0",
            highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._redesenhar())

    def set_valor(self, valor):
        self.valor = max(0, min(100, valor))
        self._redesenhar()

    def _redesenhar(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w <= 1 or h <= 1:
            return
        preenchido = int(w * self.valor / 100)
        c.create_rectangle(0, 0, w, h, fill=ArduinoTheme.BG_NEUTRO, outline="")
        if preenchido > 0:
            c.create_rectangle(
                0, 0, preenchido, h,
                fill=ArduinoTheme.TEAL, outline="",
            )
            c.create_rectangle(
                0, 0, preenchido, max(1, h * 0.35),
                fill=ArduinoTheme.TEAL_LIGHT, outline="",
            )
        texto = f"{self.valor:.0f}%"
        cor_texto = "white" if self.valor > 20 else ArduinoTheme.FG_EDITOR
        c.create_text(
            w / 2, h / 2, text=texto, fill=cor_texto,
            font=("Segoe UI", 9, "bold"),
        )


# ---------------------------------------------------------------------------
# Navegador embutido (pywebview em processo separado, encaixado via Win32)
# ---------------------------------------------------------------------------
# Bloqueador de anúncios (camada 1: rede | camada 2: script na página)
_AD_HOSTS = (
    "doubleclick.net", "googlesyndication.com", "googleadservices.com",
    "googletagservices.com", "adservice.google.com", "2mdn.net",
    "adnxs.com", "advertising.com", "amazon-adsystem.com", "criteo.com",
    "criteo.net", "rubiconproject.com", "pubmatic.com", "openx.net",
    "taboola.com", "outbrain.com", "moatads.com", "adsafeprotected.com",
    "scorecardresearch.com", "casalemedia.com", "smartadserver.com",
    "adform.net", "yieldmo.com", "teads.tv", "popads.net", "popcash.net",
    "propellerads.com", "adsterra.com", "exoclick.com", "mgid.com",
    # redes de popup/redirect/push muito usadas em sites de streaming
    "juicyads.com", "clickadu.com", "hilltopads.net", "trafficjunky.com",
    "trafficfactory.biz", "adcash.com", "ad-maven.com", "admaven.com",
    "monetag.com", "profitableratecpm.com", "highperformanceformat.com",
    "effectivegatecpm.com", "realsrv.com", "tsyndicate.com", "a-ads.com",
    "onclickads.net", "onclkds.com", "adskeeper.com", "revcontent.com",
    "bidvertiser.com", "zedo.com", "histats.com", "richads.com",
    "adspyglass.com", "pushnami.com",
)
_AD_CAMINHOS = (
    "youtube.com/pagead/", "youtube.com/api/stats/ads",
    "youtube.com/ptracking", "youtube.com/get_midroll_",
    "youtube.com/api/stats/qoe?adformat", "/pagead/ads", "/pagead/viewthroughconversion",
    "/youtubei/v1/player/ad_break",
)


def _url_de_anuncio(url):
    try:
        u = str(url).lower()
        resto = u.split("://", 1)[-1]
        host = resto.split("/", 1)[0].split(":", 1)[0]
        for h in _AD_HOSTS:
            if host == h or host.endswith("." + h):
                return True
        for c in _AD_CAMINHOS:
            if c in resto:
                return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# MODO ESTRITO: sites onde NADA pode entrar (anúncio, som fantasma, popup,
# redirecionamento). É ativado quando o endereço contém uma destas palavras.
# Para incluir outro site, basta acrescentar uma palavra do endereço aqui.
# ---------------------------------------------------------------------------
_SITES_ESTRITOS = ("redecanais", "rede-canais", "redecanal")

# Palavras de endereço que, mesmo dentro do site estrito, são tratadas como
# permitidas na navegação principal (ex.: um espelho do site com outro nome).
_NAV_EXTRA_PERMITIDOS = ()

_RE_URL_SUSPEITA = re.compile(
    r"(redirect|redir\.|/out\.|/go\.php|/click|track|affiliat|popunder|popup|"
    r"/ads?[/.?_-]|banner|sponsor)",
    re.IGNORECASE,
)


def _host_de(url):
    try:
        resto = str(url).split("://", 1)[-1]
        resto = resto.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        return resto.split("@")[-1].split(":", 1)[0].lower()
    except Exception:
        return ""


def _rotulo_site(host):
    """Nome principal do site, ignorando o final (.gs, .com.br, .mov ...)."""
    partes = [p for p in host.split(".") if p]
    if (
        len(partes) >= 3 and len(partes[-1]) == 2
        and partes[-2] in ("com", "net", "org", "gov", "edu", "co")
    ):
        return partes[-3]
    if len(partes) >= 2:
        return partes[-2]
    return host


def _eh_site_estrito(url):
    h = _host_de(url)
    return bool(h) and any(k in h for k in _SITES_ESTRITOS)


def _mesmo_site(url_a, url_b):
    a, b = _host_de(url_a), _host_de(url_b)
    if not a or not b:
        return False
    if _rotulo_site(a) == _rotulo_site(b):
        return True
    if any(k in a and k in b for k in _SITES_ESTRITOS):
        return True
    return any(k in b for k in _NAV_EXTRA_PERMITIDOS)


ADBLOCK_JS = r"""
(function(){
  if (window.__i9universal_adblock === true) return;
  window.__i9universal_adblock = true;

  var host = (window.location && window.location.hostname) ? window.location.hostname.toLowerCase() : "";

  /* Modo estrito: Redecanais e afins (inclusive o player dentro de iframes de outro dominio) */
  var KW_ESTRITO = __SITES_ESTRITOS__;
  var ESTRITO = false;
  try {
    var _temKw = function(s){
      s = String(s || '').toLowerCase();
      for (var q = 0; q < KW_ESTRITO.length; q++) { if (s.indexOf(KW_ESTRITO[q]) !== -1) return true; }
      return false;
    };
    if (_temKw(host)) ESTRITO = true;
    else if (window !== window.top) {
      var _ao = window.location.ancestorOrigins;
      if (_ao) { for (var q2 = 0; q2 < _ao.length; q2++) { if (_temKw(_ao[q2])) ESTRITO = true; } }
      if (!ESTRITO && _temKw(document.referrer)) ESTRITO = true;
    }
    if (/(^|\.)(youtube\.com|youtu\.be|youtube-nocookie\.com|googlevideo\.com|ytimg\.com)$/.test(host)) ESTRITO = false;
  } catch(e) {}

  /* 0) Modulo Google IMA SDK Defuser (uBlock / AdGuard style) */
  try {
    var noop = function(){};
    var imaMock = {
      AdDisplayContainer: function(){ this.initialize = noop; this.destroy = noop; },
      AdsLoader: function(){
        this.contentComplete = noop;
        this.requestAds = function(){
          var self = this;
          setTimeout(function(){
            if (self._listeners && self._listeners['adError']) {
              self._listeners['adError'].forEach(function(cb){
                try {
                  cb({
                    getError: function(){
                      return {
                        getErrorCode: function(){ return 1005; },
                        getMessage: function(){ return 'AdBlock: Ads disabled'; }
                      };
                    }
                  });
                } catch(e) {}
              });
            }
          }, 10);
        };
        this._listeners = {};
        this.addEventListener = function(evt, cb){
          if (!this._listeners[evt]) this._listeners[evt] = [];
          this._listeners[evt].push(cb);
        };
      },
      AdsManagerLoadedEvent: { Type: { ADS_MANAGER_LOADED: 'adsManagerLoaded' } },
      AdErrorEvent: { Type: { AD_ERROR: 'adError' } },
      AdEvent: { Type: { ALL_ADS_COMPLETED: 'allAdsCompleted', CONTENT_PAUSE_REQUESTED: 'pause', CONTENT_RESUME_REQUESTED: 'resume' } },
      AdsRequest: function(){},
      AdsRenderingSettings: function(){},
      ViewMode: { NORMAL: 'normal', FULLSCREEN: 'fullscreen' },
      settings: { setAutoPlayAdBreaks: noop, setDisableCustomPlaybackForIOS10Plus: noop }
    };

    try {
      Object.defineProperty(window, 'google', {
        get: function() { return { ima: imaMock }; },
        set: function() {},
        configurable: true
      });
    } catch(e) {
      window.google = window.google || {};
      window.google.ima = imaMock;
    }
  } catch(e) {}

  /* 1) Modulo Universal: Anti-popup, trava de auto-fullscreen e neutralizacao de overlays */
  try {
    var _safeWin = {
      focus: function(){},
      blur: function(){},
      close: function(){},
      closed: false,
      document: { write: function(){}, location: {} },
      location: { href: '' }
    };
    var _origOpen = window.open;
    window.open = function(url, target, features) {
      if (!url || url === 'about:blank') return _safeWin;
      var u = String(url).toLowerCase();
      var adWords = ['bet', 'cassino', 'casino', 'blaze', 'popads', 'propeller', 'adsterra', 'exoclick', 'doubleclick', 'traffic', 'histats', 'affiliat', 'redirect', 'track', 'chatango'];
      for (var i = 0; i < adWords.length; i++) {
        if (u.indexOf(adWords[i]) !== -1 && u.indexOf('youtube') === -1) {
          return _safeWin;
        }
      }
      try {
        if (typeof _origOpen === 'function') {
          return _origOpen.apply(window, arguments);
        }
      } catch(e) {}
      return _safeWin;
    };
  } catch (e) {}

  // Trava de requestFullscreen automatico (impede sites de forcar tela cheia sozinhos ao dar play)
  try {
    window._ydUsuarioPediuFs = false;
    document.addEventListener('click', function(e) {
      try {
        var t = e.target;
        var btn = t ? (t.closest ? t.closest('.vjs-fullscreen-control, .ytp-fullscreen-button, [title*="Fullscreen" i], [title*="fullscreen" i], [title*="Tela cheia" i], [aria-label*="Tela cheia" i], [aria-label*="Fullscreen" i], button.vjs-fullscreen-control') : null) : null;
        if (btn) {
          window._ydUsuarioPediuFs = true;
          setTimeout(function(){ window._ydUsuarioPediuFs = false; }, 1500);
        }
      } catch(err) {}
    }, true);

    document.addEventListener('keydown', function(e) {
      if (e.key === 'f' || e.key === 'F') {
        window._ydUsuarioPediuFs = true;
        setTimeout(function(){ window._ydUsuarioPediuFs = false; }, 1500);
      }
    }, true);

    var _origReq = Element.prototype.requestFullscreen || Element.prototype.webkitRequestFullscreen;
    function interceptarReqFs() {
      if (!window._ydUsuarioPediuFs) {
        return Promise.resolve();
      }
      window._ydUsuarioPediuFs = false;
      if (_origReq) return _origReq.apply(this, arguments);
      return Promise.resolve();
    }
    if (Element.prototype.requestFullscreen) Element.prototype.requestFullscreen = interceptarReqFs;
    if (Element.prototype.webkitRequestFullscreen) Element.prototype.webkitRequestFullscreen = interceptarReqFs;
  } catch(e) {}

  /* No modo estrito evita esconder por engano o player (ex.: classes tipo "anima-", "prima-") */
  var SEL_IMA = ESTRITO
    ? '.ima-ad-container, [class^="ima-"], [class*=" ima-"], [id^="ima-"]'
    : '[class*="ima-"], [id*="ima-"]';
  var CSS_UNIVERSAL = [
    'iframe[src*="doubleclick"]', 'iframe[src*="traffic"]', 'iframe[src*="histats"]',
    'iframe[src*="popads"]', 'iframe[src*="adsterra"]', 'iframe[src*="exoclick"]',
    'iframe[src*="chatango"]', SEL_IMA,
    '.vjs-ad-loading', '.vjs-ad-playing .vjs-ad-controls', 'video[title="Advertisement"]',
    '.ads-banner', '.ad-container', '[class*="popunder"]',
    '[id*="popunder"]', '.ad-overlay', '[class*="floating-ad"]',
    '[data-rc-player-gesture]', 'button[data-rc-player-gesture]', '[class*="rc-player-gesture"]',
    'div[style*="z-index: 2147483647"]:not(:has(video)):not(:has(iframe))',
    'div[style*="z-index: 999999"]:not(:has(video)):not(:has(iframe))'
  ].join(',') + '{display:none !important; visibility:hidden !important; pointer-events:none !important; width:0 !important; height:0 !important; opacity:0 !important;}' +
  'iframe[name="Player"], iframe[src*="player"], iframe[src*="server.php"], iframe[src*="embed.php"], video { display:block !important; visibility:visible !important; pointer-events:auto !important; }';

  function aplicarCssUniversal() {
    if (document.getElementById('__i9adcss_univ')) return;
    var st = document.createElement('style');
    st.id = '__i9adcss_univ';
    st.textContent = CSS_UNIVERSAL;
    (document.head || document.documentElement).appendChild(st);
  }
  try { aplicarCssUniversal(); } catch(e) {}

  function removerOverlaysFantasmas() {
    try {
      aplicarCssUniversal();
      var badElements = document.querySelectorAll('[data-rc-player-gesture], button[data-rc-player-gesture], [class*="rc-player-gesture"], .ad-overlay, [class*="floating-ad"], [class*="popunder"], [id*="popunder"], video[title="Advertisement"]');
      for (var i = 0; i < badElements.length; i++) {
        badElements[i].remove();
      }
    } catch (e) {}
  }
  removerOverlaysFantasmas();
  setInterval(removerOverlaysFantasmas, 300);

  function matarVideoAds() {
    try {
      var ads = document.querySelectorAll('video[title="Advertisement"], .ima-ad-container video, [class*="ima-controls"] video');
      for (var i = 0; i < ads.length; i++) {
        var v = ads[i];
        v.muted = true;
        v.currentTime = v.duration || 999999;
        try { v.dispatchEvent(new Event('ended')); } catch(err) {}
      }
    } catch(e) {}
  }
  setInterval(matarVideoAds, 250);

  /* 2) Monitor de Fullscreen Deterministico (Universal: Top e Iframes) */
  try {
    var _ydFsSeq = 0;
    var _ydUltimoEstadoFs = false;

    function notificarFs(ativo) {
      if (ativo === _ydUltimoEstadoFs) return;
      _ydUltimoEstadoFs = !!ativo;
      try {
        if (window !== window.top) {
          window.top.postMessage({ __youdown_fs__: ativo ? 1 : 0 }, '*');
        }
      } catch(e) {}
      try {
        if (window === window.top) {
          _ydFsSeq++;
          var h = window.location.hash || '';
          var cleanH = h.replace(/&?__youdown_fs_[a-zA-Z0-9_]+__=\d+/g, '').replace(/^#$/, '');
          var tag = ativo ? ('__youdown_fs_in__=' + _ydFsSeq) : ('__youdown_fs_out__=' + _ydFsSeq);
          window.location.hash = '#' + (cleanH ? (cleanH + '&' + tag) : tag);
        }
      } catch(e) {}
    }

    function atualizarEstadoFs() {
      var docFs = !!(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
      );
      var vjsFs = false;
      var vjsEl = document.querySelector('.vjs-fullscreen, .video-js.vjs-fullscreen');
      if (vjsEl) {
        var isAd = vjsEl.classList.contains('vjs-ad-playing') || vjsEl.classList.contains('vjs-ad-loading');
        if (!isAd && window._ydUsuarioPediuFs) {
          vjsFs = true;
        }
      }
      var isFs = docFs || vjsFs;
      notificarFs(isFs);
    }

    document.addEventListener('fullscreenchange', atualizarEstadoFs, true);
    document.addEventListener('webkitfullscreenchange', atualizarEstadoFs, true);
    document.addEventListener('mozfullscreenchange', atualizarEstadoFs, true);
    document.addEventListener('MSFullscreenChange', atualizarEstadoFs, true);
    document.addEventListener('webkitbeginfullscreen', function(){ notificarFs(true); }, true);
    document.addEventListener('webkitendfullscreen', function(){ notificarFs(false); }, true);

    document.addEventListener('click', function(e) {
      try {
        var t = e.target;
        var btn = t ? (t.closest ? t.closest('.vjs-fullscreen-control, .ytp-fullscreen-button, [title*="Fullscreen" i], [title*="fullscreen" i], [title*="Tela cheia" i], [aria-label*="Tela cheia" i], [aria-label*="Fullscreen" i], button.vjs-fullscreen-control') : null) : null;
        if (btn) {
          window._ydUsuarioPediuFs = true;
          setTimeout(function(){ window._ydUsuarioPediuFs = false; }, 1500);
          setTimeout(atualizarEstadoFs, 200);
          setTimeout(atualizarEstadoFs, 500);
        }
      } catch(err) {}
    }, false);

    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' || e.keyCode === 27) {
        notificarFs(false);
        try {
          if (document.exitFullscreen) document.exitFullscreen();
          else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
          var yt = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
          if (yt && yt.classList && yt.classList.contains('ytp-fullscreen')) {
            if (typeof yt.toggleFullscreen === 'function') yt.toggleFullscreen();
            yt.classList.remove('ytp-fullscreen');
          }
        } catch(ex) {}
      } else if (e.key === 'f' || e.key === 'F') {
        window._ydUsuarioPediuFs = true;
        setTimeout(function(){ window._ydUsuarioPediuFs = false; }, 1500);
        setTimeout(atualizarEstadoFs, 200);
        setTimeout(atualizarEstadoFs, 500);
      }
    }, true);

    if (window === window.top) {
      window.addEventListener('message', function(ev) {
        try {
          if (ev.data && typeof ev.data.__youdown_fs__ !== 'undefined') {
            notificarFs(ev.data.__youdown_fs__ === 1);
          }
        } catch(e) {}
      }, true);
    }
  } catch(e) {}

  /* 2.5) MODO ESTRITO (Redecanais e afins): nada de anuncio, som fantasma, popup ou redirecionamento */
  if (ESTRITO) { try {
    /* Chaves de seguranca: se algo do player quebrar, desligue o item suspeito aqui. */
    var CFG = {
      audioTag: true,     /* bloqueia <audio> e new Audio() (anuncio sonoro sem imagem) */
      escondidos: true,   /* remove video tocando escondido e iframes minusculos de terceiros */
      fantasmas: true,    /* remove camadas transparentes que cobrem a tela para roubar o clique */
      rede: true,         /* barra fetch/XHR/script/iframe/video vindos de redes de anuncio */
      sw: true            /* barra service worker e notificacoes push de anuncio */
    };
    var AD_HOSTS = __AD_HOSTS__;
    var AD_PATHS = __AD_CAMINHOS__;
    var RE_AD_URL = /(^|[\/._?&=-])(ads?|adserver|adserving|adsbygoogle|adsystem|popunder|popads?|vpaid|vast[0-9]*|preroll|pre-roll)([\/._?&=-]|$)/i;
    function nop() {}

    /* ---------- utilitarios de endereco ---------- */
    function hostDe(u) { try { return new URL(u, location.href).hostname.toLowerCase(); } catch (e) { return ''; } }
    function rotulo(h) {
      var p = h.split('.').filter(Boolean);
      if (p.length >= 3 && p[p.length - 1].length === 2 && /^(com|net|org|gov|edu|co)$/.test(p[p.length - 2])) return p[p.length - 3];
      return p.length >= 2 ? p[p.length - 2] : h;
    }
    var ROT_PAGINA = rotulo(host);
    function mesmoSite(u) { var h = hostDe(u); return !!h && (rotulo(h) === ROT_PAGINA || (_temKw(h) && _temKw(host))); }
    function urlAd(u) {
      try {
        if (!u) return false;
        var s = String(u);
        if (/^(data|blob|about|javascript):/i.test(s)) return false;
        var x = new URL(s, location.href), h = x.hostname.toLowerCase(), i;
        for (i = 0; i < AD_HOSTS.length; i++) { if (h === AD_HOSTS[i] || h.slice(-(AD_HOSTS[i].length + 1)) === '.' + AD_HOSTS[i]) return true; }
        var resto = (h + x.pathname + x.search).toLowerCase();
        for (i = 0; i < AD_PATHS.length; i++) { if (resto.indexOf(AD_PATHS[i]) !== -1) return true; }
        return RE_AD_URL.test(x.pathname + x.search);
      } catch (e) { return false; }
    }

    /* ---------- 1) popup, dialogos, push ---------- */
    var _fake = {
      focus: nop, blur: nop, close: nop, closed: false, postMessage: nop,
      document: { write: nop, writeln: nop, close: nop, location: {} }, location: { href: '' }
    };
    window.open = function () { return _fake; };
    window.alert = nop;
    window.confirm = function () { return false; };
    window.prompt = function () { return null; };
    if (CFG.sw) {
      try { if (navigator.serviceWorker) navigator.serviceWorker.register = function () { return Promise.reject(new Error('bloqueado')); }; } catch (e) {}
      try {
        if (window.Notification) {
          Notification.requestPermission = function (cb) { if (typeof cb === 'function') cb('denied'); return Promise.resolve('denied'); };
        }
      } catch (e) {}
    }

    /* ---------- 2) rede: nada de anuncio carregando por dentro da pagina ---------- */
    function erroAssinc(el) { setTimeout(function () { try { el.dispatchEvent(new Event('error')); } catch (e) {} }, 0); }
    if (CFG.rede) {
      try {
        var _fetch = window.fetch;
        if (_fetch) {
          window.fetch = function (inp) {
            try {
              var u = (typeof inp === 'string') ? inp : ((inp && inp.url) || String(inp));
              if (urlAd(u)) return Promise.resolve(new Response(null, { status: 204 }));
            } catch (e) {}
            return _fetch.apply(this, arguments);
          };
        }
      } catch (e) {}
      try {
        var _xo = XMLHttpRequest.prototype.open, _xs = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.open = function (m, u) { try { this.__ydBloq = urlAd(u); } catch (e) {} return _xo.apply(this, arguments); };
        XMLHttpRequest.prototype.send = function () {
          if (this.__ydBloq) {
            var x = this;
            setTimeout(function () { try { x.dispatchEvent(new Event('error')); x.dispatchEvent(new Event('loadend')); } catch (e) {} }, 0);
            return;
          }
          return _xs.apply(this, arguments);
        };
      } catch (e) {}
      var travarSrc = function (proto, nome, aoBloquear) {
        try {
          var d = Object.getOwnPropertyDescriptor(proto, nome);
          if (!d || !d.set) return;
          Object.defineProperty(proto, nome, {
            configurable: true, enumerable: d.enumerable, get: d.get,
            set: function (v) { if (urlAd(v)) { aoBloquear(this); return; } d.set.call(this, v); }
          });
        } catch (e) {}
      };
      travarSrc(HTMLScriptElement.prototype, 'src', erroAssinc);
      travarSrc(HTMLIFrameElement.prototype, 'src', function (el) { el.__ydBloq = true; try { el.remove(); } catch (e) {} });
      travarSrc(HTMLMediaElement.prototype, 'src', erroAssinc);
      try {
        var _sa = Element.prototype.setAttribute;
        Element.prototype.setAttribute = function (n, v) {
          try {
            if (typeof n === 'string' && n.toLowerCase() === 'src') {
              var t = this.tagName;
              if ((t === 'SCRIPT' || t === 'IFRAME' || t === 'VIDEO' || t === 'AUDIO' || t === 'SOURCE' || t === 'EMBED') && urlAd(v)) {
                if (t === 'IFRAME') { this.__ydBloq = true; try { this.remove(); } catch (e) {} } else { erroAssinc(this); }
                return;
              }
            }
          } catch (e) {}
          return _sa.apply(this, arguments);
        };
      } catch (e) {}
    }

    /* ---------- 3) deteccao de elemento de anuncio por classe/id ---------- */
    var RE_TOK_AD = /^(ad|ads|adv|advert|advertisement|adsbox|adbox|ad-container|ad-overlay|ads-banner|preroll|pre-roll|popunder|sponsor|sponsored|vast|vpaid|ima-ad-container)$/;
    function tokenAd(t) {
      t = String(t || '').toLowerCase();
      if (!t || t.indexOf('vjs-') === 0) return false; /* vjs-ad-playing etc. pertencem ao player */
      if (RE_TOK_AD.test(t)) return true;
      if (/gpt-ad|google_ads|adsbygoogle/.test(t)) return true;
      return /^(ads?|adv)[-_]/.test(t) || /[-_](ads?|adv)$/.test(t);
    }
    function elAd(el) {
      try {
        if (tokenAd(el.id)) return true;
        var c = el.className;
        if (c && typeof c !== 'string') c = c.baseVal || '';
        var ts = String(c || '').split(/\s+/);
        for (var i = 0; i < ts.length; i++) { if (tokenAd(ts[i])) return true; }
        if (el.getAttribute && String(el.getAttribute('title') || '').toLowerCase() === 'advertisement') return true;
      } catch (e) {}
      return false;
    }
    function ancestralAd(el) {
      var n = 0;
      while (el && el.nodeType === 1 && n < 8) { if (elAd(el)) return true; el = el.parentElement; n++; }
      return false;
    }

    /* ---------- 4) midia: some o som de verdade, nao so a imagem ---------- */
    function calar(el, remover) {
      try { el.muted = true; el.volume = 0; } catch (e) {}
      try { el.pause(); } catch (e) {}
      if (remover) {
        try { el.removeAttribute('src'); el.load(); } catch (e) {}
        try { if (el.parentNode) el.parentNode.removeChild(el); } catch (e) {}
      }
    }
    function midiaAd(el) {
      try {
        if (CFG.audioTag && el.tagName === 'AUDIO') return true;
        if (urlAd(el.currentSrc || el.src)) return true;
        if (ancestralAd(el)) return true;
      } catch (e) {}
      return false;
    }
    try {
      var _play = HTMLMediaElement.prototype.play;
      HTMLMediaElement.prototype.play = function () {
        try { if (midiaAd(this)) { calar(this, true); return Promise.resolve(); } } catch (e) {}
        return _play.apply(this, arguments);
      };
    } catch (e) {}

    var _ocultoCont = (typeof WeakMap === 'function') ? new WeakMap() : null;
    function oculto(el) {
      try {
        var r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) return true;
        if (r.right < -2000 || r.left < -2000) return true;
        var n = el, k = 0;
        while (n && n.nodeType === 1 && k < 12) {
          var cs = getComputedStyle(n);
          if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.02) return true;
          n = n.parentElement; k++;
        }
      } catch (e) {}
      return false;
    }

    /* ---------- 5) camadas fantasma (clique roubado) ---------- */
    var RE_UI = /(^|[\s_-])(vjs|plyr|jw|jwplayer|mejs|fp|flowplayer|dplayer|art|clappr|fluid|xgplayer|vime|shaka|ytp|html5|player|control|controls|poster|loading|spinner)([\s_-]|$)/i;
    function fantasma(el) {
      try {
        if (!el || el === document.body || el === document.documentElement) return false;
        var t = el.tagName;
        if (t === 'VIDEO' || t === 'IFRAME' || t === 'CANVAS' || t === 'OBJECT' || t === 'EMBED' || t === 'svg' || t === 'SVG') return false;
        var cn = (typeof el.className === 'string') ? el.className : '';
        if (RE_UI.test(cn) || RE_UI.test(el.id || '')) return false;
        var cs = getComputedStyle(el);
        if (cs.position !== 'fixed' && cs.position !== 'absolute') return false;
        var r = el.getBoundingClientRect();
        if (r.width < window.innerWidth * 0.6 || r.height < window.innerHeight * 0.6) return false;
        if (el.querySelector('video,iframe,canvas,audio,img,svg,button,input,a')) return false;
        if (String(el.textContent || '').trim().length > 0) return false;
        var bg = cs.backgroundColor;
        var transp = parseFloat(cs.opacity) <= 0.05 || ((bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent') && cs.backgroundImage === 'none');
        return !!transp;
      } catch (e) { return false; }
    }

    /* ---------- 6) varredura periodica + observador de DOM ---------- */
    var RE_JOGADOR = /player|embed|server\.php|stream|video/i;
    function varrer() {
      try {
        var i, e;
        /* audio: so anuncio usa */
        if (CFG.audioTag) {
          var as = document.querySelectorAll('audio');
          for (i = 0; i < as.length; i++) calar(as[i], true);
        }
        /* videos */
        var vs = document.querySelectorAll('video'), vis = [], oc = [];
        for (i = 0; i < vs.length; i++) { (oculto(vs[i]) ? oc : vis).push(vs[i]); }
        for (i = 0; i < vis.length; i++) { if (midiaAd(vis[i])) calar(vis[i], true); }
        if (CFG.escondidos) {
          for (i = 0; i < oc.length; i++) {
            var v = oc[i];
            if (midiaAd(v)) { calar(v, true); continue; }
            if (v.paused) continue;
            var n = ((_ocultoCont && _ocultoCont.get(v)) || 0) + 1;
            if (_ocultoCont) _ocultoCont.set(v, n);
            if (n >= 4 || vis.length > 0) calar(v, true);
          }
        }
        /* iframes de anuncio / minusculos de terceiros */
        var fr = document.querySelectorAll('iframe');
        for (i = 0; i < fr.length; i++) {
          var f = fr[i], src = f.getAttribute('src') || '';
          if (f.__ydBloq || urlAd(src) || elAd(f)) { try { f.remove(); } catch (e2) {} continue; }
          if (CFG.escondidos && src && !/^(about|javascript|data):/i.test(src) && !mesmoSite(src) &&
              !RE_JOGADOR.test(src + ' ' + (f.name || '') + ' ' + (f.id || ''))) {
            var rr = f.getBoundingClientRect();
            if ((rr.width <= 5 && rr.height <= 5) || rr.left < -2000 || rr.top < -2000) { try { f.remove(); } catch (e3) {} }
          }
        }
        /* camadas transparentes por cima do player */
        if (CFG.fantasmas && document.body && document.elementsFromPoint) {
          var pts = [[0.5, 0.5], [0.3, 0.4], [0.7, 0.6]];
          for (i = 0; i < pts.length; i++) {
            var pilha = document.elementsFromPoint(window.innerWidth * pts[i][0], window.innerHeight * pts[i][1]);
            for (var k = 0; k < pilha.length; k++) {
              e = pilha[k];
              if (e.tagName === 'VIDEO' || e.tagName === 'IFRAME') break;
              if (fantasma(e)) { try { e.remove(); } catch (e4) {} }
            }
          }
        }
      } catch (e) {}
    }
    var _agendado = false;
    function agendar() { if (_agendado) return; _agendado = true; setTimeout(function () { _agendado = false; varrer(); }, 60); }
    try {
      new MutationObserver(function (ms) {
        for (var i = 0; i < ms.length; i++) {
          var a = ms[i].addedNodes;
          for (var j = 0; j < a.length; j++) {
            var nn = a[j];
            if (nn.nodeType === 1 && nn.tagName === 'SCRIPT' && urlAd(nn.src)) { try { nn.remove(); } catch (e) {} }
          }
        }
        agendar();
      }).observe(document, { childList: true, subtree: true });
    } catch (e) {}
    setInterval(varrer, 300);

    /* ---------- 7) cliques: nada sai do site ---------- */
    document.addEventListener('click', function (ev) {
      try {
        var a = ev.target && ev.target.closest ? ev.target.closest('a[href]') : null;
        if (!a) return;
        var ext = !mesmoSite(a.href) && /^https?:/i.test(a.href);
        if (urlAd(a.href) || (ext && (a.target === '_blank' || !ev.isTrusted))) { ev.preventDefault(); ev.stopImmediatePropagation(); }
      } catch (x) {}
    }, true);
    try {
      var _ac = HTMLAnchorElement.prototype.click;
      HTMLAnchorElement.prototype.click = function () {
        try { if (urlAd(this.href) || (!mesmoSite(this.href) && /^https?:/i.test(this.href))) return; } catch (e) {}
        return _ac.apply(this, arguments);
      };
    } catch (e) {}
    document.addEventListener('submit', function (ev) {
      try {
        var f = ev.target;
        if (f && f.target === '_blank' && !mesmoSite(f.action)) { ev.preventDefault(); ev.stopImmediatePropagation(); }
      } catch (x) {}
    }, true);
  } catch (e) {} }

  /* 3) Modulo especifico para YouTube */
  if (!host.includes("youtube.com") && !host.includes("youtu.be")) return;

  var stats = window.__i9stats = {podados: 0, pulados: 0};
  var CHAVES = ['adPlacements', 'playerAds', 'adSlots', 'adBreakHeartbeatParams'];
  function podar(o){
    try {
      if (!o || typeof o !== 'object') return o;
      var alvos = [o];
      if (o.playerResponse && typeof o.playerResponse === 'object') alvos.push(o.playerResponse);
      for (var k = 0; k < alvos.length; k++) {
        for (var i = 0; i < CHAVES.length; i++) {
          if (alvos[k][CHAVES[i]] !== undefined) { delete alvos[k][CHAVES[i]]; stats.podados++; }
        }
      }
    } catch (e) {}
    return o;
  }
  try {
    var jp = JSON.parse;
    JSON.parse = function(){ return podar(jp.apply(this, arguments)); };
  } catch (e) {}
  try {
    var rj = Response.prototype.json;
    Response.prototype.json = function(){ return rj.apply(this, arguments).then(podar); };
  } catch (e) {}
  try {
    var ipr = window.ytInitialPlayerResponse;
    Object.defineProperty(window, 'ytInitialPlayerResponse', {
      configurable: true,
      get: function(){ return ipr; },
      set: function(v){ ipr = podar(v); }
    });
    if (ipr) podar(ipr);
  } catch (e) {}

  var CSS_YT = [
    '#masthead-ad','ytd-ad-slot-renderer','ytd-in-feed-ad-layout-renderer',
    'ytd-banner-promo-renderer','ytd-promoted-sparkles-web-renderer',
    'ytd-display-ad-renderer','ytd-companion-slot-renderer','#player-ads',
    '.ytp-ad-overlay-container','.ytp-ad-module','.video-ads',
    '.ytp-ad-player-overlay','.ytp-ad-player-overlay-layout',
    'ytd-action-companion-ad-renderer','ytd-player-legacy-desktop-watch-ads-renderer',
    'ytd-statement-banner-renderer','#related ytd-promoted-video-renderer',
    'ytm-promoted-sparkles-web-renderer','ad-slot-renderer',
    'ins.adsbygoogle','[id^="google_ads"]','[id^="div-gpt-ad"]',
    'iframe[src*="doubleclick.net"]','iframe[src*="googlesyndication"]',
    'iframe[src*="adservice"]'
  ].join(',') + '{display:none !important;}';
  function addCssYt(){
    if (document.getElementById('__i9adcss_yt')) return;
    var st = document.createElement('style');
    st.id = '__i9adcss_yt';
    st.textContent = CSS_YT;
    (document.head || document.documentElement).appendChild(st);
  }
  addCssYt();

  var mutouPorAd = false;
  function anuncioTocando(player){
    if (!player) return false;
    if (player.classList.contains('ad-showing') || player.classList.contains('ad-interrupting')) return true;
    return !!document.querySelector('.ytp-ad-player-overlay, .ytp-ad-text, .ytp-ad-preview-text, .ytp-ad-simple-ad-badge');
  }
  function tickYt(){
    try {
      addCssYt();
      var player = document.querySelector('.html5-video-player');
      var v = document.querySelector('video.html5-main-video') || document.querySelector('video');
      if (anuncioTocando(player) && v) {
        if (!mutouPorAd) { mutouPorAd = true; v.dataset.i9m = v.muted ? '1' : '0'; stats.pulados++; }
        v.muted = true;
        try { v.playbackRate = 16; } catch (e) {}
        if (isFinite(v.duration) && v.duration > 0) { v.currentTime = Math.max(v.duration - 0.05, 0); }
      } else if (mutouPorAd && v) {
        mutouPorAd = false;
        v.muted = (v.dataset.i9m === '1');
        v.playbackRate = 1;
      }
      var botoes = document.querySelectorAll(
        '.ytp-skip-ad-button,.ytp-ad-skip-button,.ytp-ad-skip-button-modern,' +
        '.ytp-skip-ad-button__text,.ytp-ad-overlay-close-button');
      for (var i = 0; i < botoes.length; i++) { botoes[i].click(); }
    } catch (e) {}
  }
  setInterval(tickYt, 200);
})();
"""

# Injeta no script as listas definidas em Python (uma única fonte de verdade)
ADBLOCK_JS = (
    ADBLOCK_JS
    .replace("__AD_HOSTS__", json.dumps(list(_AD_HOSTS)))
    .replace("__AD_CAMINHOS__", json.dumps(list(_AD_CAMINHOS)))
    .replace("__SITES_ESTRITOS__", json.dumps(list(_SITES_ESTRITOS)))
)



# Módulo de banners (filtro automático nos sites estritos, regras do usuário e conta-gotas)
JS_BANNERS = r"""/* Banners: filtro automatico (sites estritos), regras do usuario e conta-gotas "Bloquear um anuncio". */
(function () {
  if (window.__yd_banners) return; window.__yd_banners = 1;
  var KW = __KW__;
  var host = String(location.hostname || '').toLowerCase();
  var TOPO = (window === window.top);

  function temKw(s) { s = String(s || '').toLowerCase(); for (var i = 0; i < KW.length; i++) { if (s.indexOf(KW[i]) !== -1) return true; } return false; }
  var ehYt = /(^|\.)(youtube\.com|youtu\.be|youtube-nocookie\.com|googlevideo\.com|ytimg\.com)$/.test(host);
  var ESTRITO = !ehYt && temKw(host);

  function rotulo(h) {
    var p = String(h || '').split('.').filter(Boolean);
    if (p.length >= 3 && p[p.length - 1].length === 2 && /^(com|net|org|gov|edu|co)$/.test(p[p.length - 2])) return p[p.length - 3];
    return p.length >= 2 ? p[p.length - 2] : String(h || '');
  }
  function regHost(h) {
    var p = String(h || '').split('.').filter(Boolean);
    if (p.length >= 3 && p[p.length - 1].length === 2 && /^(com|net|org|gov|edu|co)$/.test(p[p.length - 2])) return p.slice(-3).join('.');
    return p.slice(-2).join('.');
  }
  var MEU_ROT = rotulo(host);
  function urlDe(u) { try { return new URL(u, location.href); } catch (e) { return null; } }
  function mesmoSite(u) {
    var x = urlDe(u); if (!x) return false;
    var h = x.hostname.toLowerCase();
    return !!h && (rotulo(h) === MEU_ROT || (temKw(h) && temKw(host)));
  }
  function cssEsc(s) { return (window.CSS && CSS.escape) ? CSS.escape(s) : String(s).replace(/[^\w-]/g, '\\$&'); }
  function diag(t, d) {
    try { if (TOPO) { (window.__ydDiag = window.__ydDiag || []).push({ t: t, d: String(d == null ? '' : d).slice(0, 160), f: host }); } } catch (e) {}
  }

  /* ---------- apostas / cassino ---------- */
  var PALAVRAS_APOSTA = ['bet', 'bets', 'cassino', 'casino', 'blaze', 'tigrinho', 'aposta', 'apostas', 'jackpot', 'roleta', 'slots', 'bingo', 'pixbet'];
  var NAO_BET = ['alphabet', 'alphabets', 'sorbet', 'tibet', 'gilbet'];
  function tokenAposta(t) {
    if (!t) return false;
    if (PALAVRAS_APOSTA.indexOf(t) !== -1) return true;
    if (NAO_BET.indexOf(t) !== -1) return false;
    if (t.length >= 6 && /bet$/.test(t)) return true;                                   /* chillbet, vaidebet, estrelabet */
    if (/^bet(ano|fair|way|nacional|mgm|sson|boo|vic|cris|online|pix|fast|7k|\d)/.test(t)) return true;   /* betano, bet365... */
    if (/^(1xbet|brazino|esportesdasorte|fortunetiger|fortunerabbit|tigrinho|stake)/.test(t)) return true;
    return false;
  }
  function textoAposta(s) {
    var partes = String(s || '').toLowerCase().split(/[^a-z0-9]+/);
    for (var i = 0; i < partes.length; i++) { if (tokenAposta(partes[i])) return true; }
    return false;
  }
  function urlAposta(u) { var x = urlDe(u); return !!x && textoAposta(x.hostname + x.pathname); }

  /* ---------- remover um banner e o embrulho vazio que sobra ---------- */
  function removerBanner(el, motivo, det) {
    try {
      var alvo = el;
      var a = el.closest ? el.closest('a') : null;
      if (a && !a.querySelector('video, iframe[allowfullscreen]')) alvo = a;
      for (var i = 0; i < 3; i++) {
        var p = alvo.parentElement;
        if (!p || p === document.body || p === document.documentElement) break;
        var resto = String(p.textContent || '').replace(String(alvo.textContent || ''), '').trim();
        if (p.children.length === 1 && !resto) alvo = p; else break;
      }
      diag(motivo, det || (el.getAttribute && (el.getAttribute('href') || el.getAttribute('src'))) || el.tagName);
      alvo.remove();
    } catch (e) {}
  }
  function medida(el) {
    var r = el.getBoundingClientRect();
    var w = r.width, h = r.height;
    if ((!w || !h) && el.naturalWidth) { w = el.naturalWidth; h = el.naturalHeight; }
    return { w: w, h: h };
  }
  function temImagemGrande(a) {
    if (a.querySelector('video, iframe')) return false;
    var im = a.querySelectorAll('img, picture, canvas');
    for (var i = 0; i < im.length; i++) { var m = medida(im[i]); if (m.w >= 200 && m.h >= 50) return true; }
    return false;
  }

  /* ---------- filtro automatico (so nos sites do modo estrito, so na pagina principal) ---------- */
  function varrerAuto() {
    var i, el;
    var as = document.querySelectorAll('a[href]');
    for (i = 0; i < as.length; i++) {
      el = as[i]; var href = el.href;
      if (!/^https?:/i.test(href)) continue;
      if (urlAposta(href)) { removerBanner(el, 'banner-aposta', href); continue; }
      if (!mesmoSite(href) && temImagemGrande(el)) { removerBanner(el, 'banner-externo', href); }
    }
    var ms = document.querySelectorAll('img[src], iframe[src], script[src]');
    for (i = 0; i < ms.length; i++) {
      el = ms[i];
      if (el.tagName === 'IFRAME' && el.hasAttribute('allowfullscreen')) continue;          /* player: nunca */
      var src = el.getAttribute('src') || '';
      if (urlAposta(src)) { removerBanner(el, 'banner-aposta-' + el.tagName.toLowerCase(), src); continue; }
      if (el.tagName === 'IFRAME' && !mesmoSite(src) && /^https?:/i.test(src)) {
        var m = medida(el);
        if (m.h > 0 && m.h <= 330 && m.w >= 200) removerBanner(el, 'banner-iframe', src);   /* 728x90, 300x250, 970x250... */
      }
    }
    var im = document.querySelectorAll('img[alt], a[title]');
    for (i = 0; i < im.length; i++) {
      el = im[i];
      var txt = el.getAttribute('alt') || el.getAttribute('title') || '';
      var ln = el.closest ? el.closest('a[href]') : null;
      if (txt && textoAposta(txt) && ln && !mesmoSite(ln.href)) removerBanner(el, 'banner-aposta-texto', txt);
    }
  }

  /* ---------- regras do usuario (window.__ydRegras, enviado pelo app) ---------- */
  function varrerRegras() {
    var r = window.__ydRegras; if (!r) return;
    var s = (r.sites && r.sites[MEU_ROT]) || {};
    var sels = (s.sel || []), hosts = (r.hosts || []).concat(s.host || []), i, j, el, lista;
    for (i = 0; i < sels.length; i++) {
      try { lista = document.querySelectorAll(sels[i]); } catch (e) { continue; }
      for (j = 0; j < lista.length; j++) removerBanner(lista[j], 'regra-seletor', sels[i]);
    }
    for (i = 0; i < hosts.length; i++) {
      var h = String(hosts[i]).replace(/["\\]/g, '');
      if (!h) continue;
      try { lista = document.querySelectorAll('a[href*="' + h + '"], iframe[src*="' + h + '"], img[src*="' + h + '"], script[src*="' + h + '"]'); } catch (e) { continue; }
      for (j = 0; j < lista.length; j++) removerBanner(lista[j], 'regra-anunciante', h);
    }
  }

  function varrer() {
    try { if (TOPO) { if (ESTRITO) varrerAuto(); varrerRegras(); } } catch (e) {}
  }
  if (TOPO) {
    var agendado = false;
    try {
      new MutationObserver(function () {
        if (agendado) return; agendado = true;
        setTimeout(function () { agendado = false; varrer(); }, 120);
      }).observe(document, { childList: true, subtree: true });
    } catch (e) {}
    setInterval(varrer, 700);
  }

  /* ---------- conta-gotas: clique no anuncio para bloquea-lo ---------- */
  function seletorDe(base) {
    var t = base.tagName.toLowerCase();
    if (base.id && /^[A-Za-z][\w-]{2,}$/.test(base.id) && !/\d{4,}/.test(base.id)) {
      try { if (document.querySelectorAll('#' + cssEsc(base.id)).length === 1) return '#' + cssEsc(base.id); } catch (e) {}
    }
    var url = base.getAttribute('href') || base.getAttribute('src') || '';
    var x = /^https?:/i.test(url) ? urlDe(url) : null;
    if (x && !mesmoSite(url)) return t + '[' + (t === 'a' ? 'href' : 'src') + '*="' + regHost(x.hostname) + '"]';
    var cls = (typeof base.className === 'string' ? base.className : '').trim().split(/\s+/).filter(function (c) { return /^[A-Za-z_-][\w-]*$/.test(c) && !/\d{3,}/.test(c); }).slice(0, 3);
    if (cls.length) {
      var s = t + '.' + cls.map(cssEsc).join('.');
      try { if (document.querySelectorAll(s).length <= 3) return s; } catch (e) {}
    }
    var partes = [], n = base;
    for (var d = 0; d < 4 && n && n !== document.body && n.parentElement; d++) {
      var irm = Array.prototype.filter.call(n.parentElement.children, function (c) { return c.tagName === n.tagName; });
      partes.unshift(n.tagName.toLowerCase() + (irm.length > 1 ? ':nth-of-type(' + (irm.indexOf(n) + 1) + ')' : ''));
      n = n.parentElement;
    }
    return 'body > ' + partes.join(' > ');
  }
  function descrever(e) {
    var base = (e.closest && e.closest('a[href]')) || e;
    var url = base.getAttribute('href') || base.getAttribute('src') || '';
    var x = /^https?:/i.test(url) ? urlDe(url) : null;
    var ext = (x && !mesmoSite(url)) ? regHost(x.hostname) : '';
    return { el: base, sel: seletorDe(base), host: ext, desc: base.tagName.toLowerCase() + (ext ? ' → ' + ext : '') };
  }

  window.__ydPick = null;
  window.__ydPicker = function () {
    if (!TOPO || window.__ydPickerAtivo) return;
    window.__ydPickerAtivo = true; window.__ydPick = null;
    var dica = document.createElement('div');
    dica.setAttribute('data-yd-picker', '1');
    dica.textContent = 'Clique no anúncio para bloqueá-lo  •  Esc cancela';
    dica.style.cssText = 'position:fixed;z-index:2147483647;left:50%;top:10px;transform:translateX(-50%);background:#c62828;color:#fff;font:600 14px Segoe UI,Arial,sans-serif;padding:8px 16px;border-radius:8px;pointer-events:none;box-shadow:0 2px 10px rgba(0,0,0,.5)';
    var realce = document.createElement('div');
    realce.setAttribute('data-yd-picker', '1');
    realce.style.cssText = 'position:fixed;z-index:2147483646;pointer-events:none;outline:3px solid #e53935;background:rgba(229,57,53,.18);display:none';
    document.documentElement.appendChild(dica);
    document.documentElement.appendChild(realce);
    var ifs = document.querySelectorAll('iframe'), salvos = [], i;
    for (i = 0; i < ifs.length; i++) { salvos.push([ifs[i], ifs[i].style.pointerEvents]); ifs[i].style.pointerEvents = 'none'; }

    function alvoEm(x, y) {
      var l = document.elementsFromPoint ? document.elementsFromPoint(x, y) : [document.elementFromPoint(x, y)];
      for (var k = 0; k < l.length; k++) {
        var e = l[k];
        if (!e || (e.getAttribute && e.getAttribute('data-yd-picker'))) continue;
        if (e === document.documentElement || e === document.body) continue;
        return e;
      }
      return null;
    }
    function mover(ev) {
      var e = alvoEm(ev.clientX, ev.clientY);
      if (!e) { realce.style.display = 'none'; return; }
      var r = e.getBoundingClientRect();
      realce.style.cssText = 'position:fixed;z-index:2147483646;pointer-events:none;outline:3px solid #e53935;background:rgba(229,57,53,.18);left:' + r.left + 'px;top:' + r.top + 'px;width:' + r.width + 'px;height:' + r.height + 'px';
    }
    function limpar() {
      document.removeEventListener('mousemove', mover, true);
      document.removeEventListener('click', clicar, true);
      document.removeEventListener('mousedown', engolir, true);
      document.removeEventListener('mouseup', engolir, true);
      document.removeEventListener('keydown', tecla, true);
      for (var k = 0; k < salvos.length; k++) salvos[k][0].style.pointerEvents = salvos[k][1];
      try { dica.remove(); realce.remove(); } catch (e) {}
      window.__ydPickerAtivo = false;
    }
    function engolir(ev) { ev.preventDefault(); ev.stopPropagation(); ev.stopImmediatePropagation(); }
    function clicar(ev) {
      engolir(ev);
      var e = alvoEm(ev.clientX, ev.clientY);
      limpar();
      if (!e) { window.__ydPick = { cancelado: true }; return; }
      var info = descrever(e);
      removerBanner(info.el, 'conta-gotas', info.sel);
      window.__ydPick = { sel: info.sel, host: info.host, desc: info.desc };
    }
    function tecla(ev) {
      if (ev.key === 'Escape') { engolir(ev); limpar(); window.__ydPick = { cancelado: true }; }
    }
    document.addEventListener('mousemove', mover, true);
    document.addEventListener('click', clicar, true);
    document.addEventListener('mousedown', engolir, true);
    document.addEventListener('mouseup', engolir, true);
    document.addEventListener('keydown', tecla, true);
    setTimeout(function () { if (window.__ydPickerAtivo) { limpar(); window.__ydPick = { cancelado: true }; } }, 90000);
  };
})();
""".replace("__KW__", json.dumps(list(_SITES_ESTRITOS)))

# ===========================================================================
# NAVEGADOR COMPLETO (abas, histórico, favoritos, autocompletar, etc.)
# ---------------------------------------------------------------------------
# Parte 1: dados (histórico, favoritos, configurações) e lógica da barra de
# endereço. Tudo aqui é Python puro, sem interface.
# ===========================================================================
import uuid
import math
import html as _html
import urllib.parse
import urllib.request
from html.parser import HTMLParser

_DIR_NAV = os.path.join(os.path.expanduser("~"), ".youdown")


def _ler_json(caminho, padrao):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return padrao


def _gravar_json(caminho, dados):
    """Grava de forma atômica (arquivo temporário + troca), sem corromper em queda."""
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        tmp = caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False)
        os.replace(tmp, caminho)
        return True
    except Exception:
        return False


# ----------------------------------------------------------------- buscas
_MOTORES_BUSCA = {
    "youtube": ("YouTube", "https://www.youtube.com/results?search_query={}", "yt"),
    "google": ("Google", "https://www.google.com/search?q={}", "g"),
    "duckduckgo": ("DuckDuckGo", "https://duckduckgo.com/?q={}", "ddg"),
    "bing": ("Bing", "https://www.bing.com/search?q={}", "bing"),
}
_URL_SUGESTOES = {
    "youtube": "https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&q={}",
    "google": "https://suggestqueries.google.com/complete/search?client=firefox&q={}",
    "duckduckgo": "https://duckduckgo.com/ac/?type=list&q={}",
    "bing": "https://api.bing.com/osjson.aspx?query={}",
}
_RE_ESQUEMA = re.compile(r"^[a-z][a-z0-9+.\-]*://", re.I)
_RE_DOMINIO = re.compile(r"^(?:[\w\-]+\.)+[a-z]{2,}(?::\d+)?(?:[/?#]\S*)?$", re.I)
_RE_IP_LOCAL = re.compile(r"^(?:localhost|\d{1,3}(?:\.\d{1,3}){3})(?::\d+)?(?:[/?#]\S*)?$", re.I)
_RE_MARCA_CMD = re.compile(r"[#&]?__youdown_cmd__=([a-z0-9_]+)\.(\d+)")
_RE_MARCA_FS = re.compile(r"&?__youdown_fs_[a-zA-Z0-9_]+__=\d+")


def _limpar_marcas(url):
    """Tira da URL as marcas internas (tela cheia e comandos de atalho)."""
    url = _RE_MARCA_CMD.sub("", url or "")
    url = _RE_MARCA_FS.sub("", url)
    return url.rstrip("#")


def _url_de_busca(motor, texto):
    modelo = _MOTORES_BUSCA.get(motor, _MOTORES_BUSCA["youtube"])[1]
    return modelo.format(urllib.parse.quote_plus(texto))


def _interpretar_entrada(texto, motor="youtube"):
    """O que o usuário digitou vira ('url', endereço) ou ('busca', endereço da busca)."""
    t = (texto or "").strip()
    if not t:
        return (None, None)
    if t.lower() == "about:blank":
        return ("url", t)
    if _RE_ESQUEMA.match(t):
        if t.lower().startswith(("http://", "https://")):
            return ("url", t)
        return ("busca", _url_de_busca(motor, t))
    partes = t.split(None, 1)
    if len(partes) == 2:
        for chave, (_n, _m, atalho) in _MOTORES_BUSCA.items():
            if partes[0].lower() == atalho:
                return ("busca", _url_de_busca(chave, partes[1]))
    if " " not in t:
        if _RE_IP_LOCAL.match(t):
            return ("url", "http://" + t)
        if _RE_DOMINIO.match(t):
            return ("url", "https://" + t)
    return ("busca", _url_de_busca(motor, t))


def _sem_esquema(url):
    u = re.sub(r"^https?://", "", str(url or ""), flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    return u.rstrip("/")


def _chave_url(url):
    """Forma normalizada para comparar endereços (ignora http/https, www, barra final, #)."""
    return _sem_esquema(str(url or "").split("#", 1)[0]).lower()


def _url_navegavel(url):
    return isinstance(url, str) and url.startswith(("http://", "https://")) and len(url) < 2048


# --------------------------------------------------------------- histórico
class HistoricoNavegador:
    """Páginas visitadas. Guarda cada visita (para agrupar por dia/apagar por período)
    e um resumo por página (título, contagem, última visita) para o autocompletar."""

    LIMITE_VISITAS = 20000

    def __init__(self, caminho=None):
        self.caminho = caminho or os.path.join(_DIR_NAV, "historico.json")
        self.paginas = {}
        self.visitas = []
        self._sujo = False
        self._carregar()

    def _carregar(self):
        d = _ler_json(self.caminho, {})
        if not isinstance(d, dict):
            return
        pgs, vis = d.get("paginas"), d.get("visitas")
        if isinstance(pgs, dict):
            for u, p in pgs.items():
                if isinstance(p, dict) and _url_navegavel(u):
                    self.paginas[u] = {
                        "t": str(p.get("t", "")), "n": int(p.get("n", 1) or 1),
                        "u": float(p.get("u", 0) or 0),
                    }
        if isinstance(vis, list):
            for v in vis:
                if isinstance(v, list) and len(v) == 2 and v[1] in self.paginas:
                    try:
                        self.visitas.append([float(v[0]), v[1]])
                    except Exception:
                        pass
        self.visitas.sort(key=lambda x: x[0])

    def salvar(self, forcar=False):
        if not (self._sujo or forcar):
            return True
        ok = _gravar_json(self.caminho, {"v": 1, "paginas": self.paginas, "visitas": self.visitas})
        if ok:
            self._sujo = False
        return ok

    def registrar(self, url, titulo="", agora=None):
        """Registra uma visita. Retorna True se contou como nova visita."""
        if not _url_navegavel(url):
            return False
        agora = time.time() if agora is None else agora
        pg = self.paginas.get(url)
        if pg is None:
            pg = self.paginas[url] = {"t": titulo or "", "n": 0, "u": 0.0}
        elif titulo:
            pg["t"] = titulo
        self._sujo = True
        if self.visitas and self.visitas[-1][1] == url and agora - self.visitas[-1][0] < 30:
            pg["u"] = agora
            return False
        pg["n"] += 1
        pg["u"] = agora
        self.visitas.append([agora, url])
        if len(self.visitas) > self.LIMITE_VISITAS:
            self.visitas = self.visitas[-self.LIMITE_VISITAS:]
            self._reconstruir()
        return True

    def atualizar_titulo(self, url, titulo):
        pg = self.paginas.get(url)
        if pg is not None and titulo and pg["t"] != titulo:
            pg["t"] = titulo
            self._sujo = True

    def _reconstruir(self):
        """Recalcula contagem/última visita a partir da lista de visitas."""
        cont, ult = {}, {}
        for ts, u in self.visitas:
            cont[u] = cont.get(u, 0) + 1
            ult[u] = max(ult.get(u, 0), ts)
        novas = {}
        for u, c in cont.items():
            base = self.paginas.get(u, {"t": ""})
            novas[u] = {"t": base.get("t", ""), "n": c, "u": ult[u]}
        self.paginas = novas
        self._sujo = True

    def remover_url(self, url):
        self.visitas = [v for v in self.visitas if v[1] != url]
        self.paginas.pop(url, None)
        self._sujo = True

    def remover_visita(self, ts, url):
        antes = len(self.visitas)
        self.visitas = [v for v in self.visitas if not (v[1] == url and abs(v[0] - ts) < 0.001)]
        if len(self.visitas) != antes:
            self._reconstruir()

    def limpar(self, desde=None):
        """Apaga tudo (desde=None) ou só as visitas a partir de 'desde' (epoch)."""
        if desde is None:
            self.visitas, self.paginas = [], {}
            self._sujo = True
            return
        self.visitas = [v for v in self.visitas if v[0] < desde]
        self._reconstruir()

    def buscar(self, texto, limite=8, agora=None):
        """Sugestões para a barra de endereço: lista de (url, título)."""
        agora = time.time() if agora is None else agora
        toks = [t for t in (texto or "").lower().split() if t]
        if not toks:
            return []
        pontuados = []
        for url, p in self.paginas.items():
            alvo = _sem_esquema(url).lower()
            tit = (p.get("t") or "").lower()
            if not all(t in alvo or t in tit for t in toks):
                continue
            dias = max(0.0, (agora - p["u"]) / 86400.0)
            pts = min(p["n"], 30) / (1.0 + dias / 14.0)
            if alvo.startswith(toks[0]):
                pts += 50
            elif alvo.split("/", 1)[0].startswith(toks[0]):
                pts += 30
            pontuados.append((pts, url, p.get("t", "")))
        pontuados.sort(key=lambda x: -x[0])
        return [(u, t) for _s, u, t in pontuados[:limite]]

    def lista(self, texto="", limite=2000):
        """Visitas mais recentes primeiro: lista de (ts, url, título)."""
        toks = [t for t in (texto or "").lower().split() if t]
        saida = []
        for ts, u in reversed(self.visitas):
            tit = self.paginas.get(u, {}).get("t", "")
            if toks:
                alvo = (_sem_esquema(u) + " " + tit).lower()
                if not all(t in alvo for t in toks):
                    continue
            saida.append((ts, u, tit))
            if len(saida) >= limite:
                break
        return saida

    def mais_visitados(self, quantos=8):
        melhores = {}
        for url, p in self.paginas.items():
            host = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
            if not host:
                continue
            atual = melhores.get(host)
            if atual is None or p["n"] > atual[1]["n"]:
                melhores[host] = (url, p)
        ordem = sorted(melhores.values(), key=lambda x: -x[1]["n"])
        return [(u, p.get("t", "")) for u, p in ordem[:quantos]]


# ---------------------------------------------------------------- favoritos
_NOMES_RAIZ = {"barra": "Barra de favoritos", "outros": "Outros favoritos"}


class _ImportadorNetscape(HTMLParser):
    """Lê o HTML de favoritos exportado por Chrome, Edge, Firefox e outros."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = {"tipo": "pasta", "titulo": "", "filhos": []}
        self.pilha = [self.raiz]
        self._cap = None
        self._buf = ""
        self._href = None
        self._pendente = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "h3":
            self._cap, self._buf = "h3", ""
        elif tag == "a":
            self._cap, self._buf = "a", ""
            self._href = dict(attrs).get("href")
        elif tag == "dl":
            if self._pendente is not None:
                self.pilha.append(self._pendente)
                self._pendente = None
            else:
                self.pilha.append(self.pilha[-1])

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "h3" and self._cap == "h3":
            pasta = {"tipo": "pasta", "titulo": self._buf.strip() or "Pasta", "filhos": []}
            self.pilha[-1]["filhos"].append(pasta)
            self._pendente = pasta
            self._cap = None
        elif tag == "a" and self._cap == "a":
            if self._href and _url_navegavel(self._href):
                self.pilha[-1]["filhos"].append({
                    "tipo": "link", "titulo": self._buf.strip() or self._href, "url": self._href,
                })
            self._cap = None
        elif tag == "dl" and len(self.pilha) > 1:
            self.pilha.pop()

    def handle_data(self, data):
        if self._cap:
            self._buf += data


class FavoritosNavegador:
    """Favoritos em árvore: duas raízes ('barra' e 'outros'), com pastas e links."""

    def __init__(self, caminho=None):
        self.caminho = caminho or os.path.join(_DIR_NAV, "favoritos.json")
        self.raizes = {"barra": [], "outros": []}
        self._sujo = False
        self._carregar()

    # -- persistência
    def _limpar_no(self, no):
        if not isinstance(no, dict):
            return None
        tipo = no.get("tipo")
        nid = str(no.get("id") or uuid.uuid4().hex[:10])
        if tipo == "link" and _url_navegavel(no.get("url")):
            return {"tipo": "link", "id": nid, "titulo": str(no.get("titulo") or no["url"]), "url": no["url"]}
        if tipo == "pasta":
            filhos = [self._limpar_no(f) for f in (no.get("filhos") or [])]
            return {"tipo": "pasta", "id": nid, "titulo": str(no.get("titulo") or "Pasta"),
                    "filhos": [f for f in filhos if f]}
        return None

    def _carregar(self):
        d = _ler_json(self.caminho, None)
        if not isinstance(d, dict) or "raizes" not in d:
            self.raizes["barra"] = [
                {"tipo": "link", "id": uuid.uuid4().hex[:10], "titulo": "YouTube", "url": "https://www.youtube.com/"},
                {"tipo": "link", "id": uuid.uuid4().hex[:10], "titulo": "Google", "url": "https://www.google.com/"},
            ]
            self._sujo = True
            return
        for chave in ("barra", "outros"):
            itens = [self._limpar_no(n) for n in (d["raizes"].get(chave) or [])]
            self.raizes[chave] = [n for n in itens if n]

    def salvar(self, forcar=False):
        if not (self._sujo or forcar):
            return True
        ok = _gravar_json(self.caminho, {"v": 1, "raizes": self.raizes})
        if ok:
            self._sujo = False
        return ok

    # -- consulta
    def _lista_de(self, pai):
        if pai in self.raizes:
            return self.raizes[pai]
        no, _l, _i = self.achar(pai)
        if no and no["tipo"] == "pasta":
            return no["filhos"]
        return None

    def achar(self, id_):
        def busca(lista):
            for i, n in enumerate(lista):
                if n["id"] == id_:
                    return n, lista, i
                if n["tipo"] == "pasta":
                    r = busca(n["filhos"])
                    if r[0]:
                        return r
            return None, None, None
        for lista in self.raizes.values():
            r = busca(lista)
            if r[0]:
                return r
        return None, None, None

    def todos_links(self):
        saida = []

        def anda(lista):
            for n in lista:
                if n["tipo"] == "link":
                    saida.append(n)
                else:
                    anda(n["filhos"])
        for lista in self.raizes.values():
            anda(lista)
        return saida

    def achar_por_url(self, url):
        ch = _chave_url(url)
        for n in self.todos_links():
            if _chave_url(n["url"]) == ch:
                return n
        return None

    def eh_favorito(self, url):
        return self.achar_por_url(url) is not None

    def buscar(self, texto, limite=5):
        toks = [t for t in (texto or "").lower().split() if t]
        if not toks:
            return []
        saida = []
        for n in self.todos_links():
            alvo = (_sem_esquema(n["url"]) + " " + n["titulo"]).lower()
            if all(t in alvo for t in toks):
                saida.append((n["url"], n["titulo"]))
            if len(saida) >= limite:
                break
        return saida

    def listar_pastas(self):
        """[(id, caminho legível)] de todas as pastas possíveis para guardar um favorito."""
        saida = []

        def anda(lista, prefixo):
            for n in lista:
                if n["tipo"] == "pasta":
                    cam = prefixo + " › " + n["titulo"]
                    saida.append((n["id"], cam))
                    anda(n["filhos"], cam)
        for chave, nome in _NOMES_RAIZ.items():
            saida.append((chave, nome))
            anda(self.raizes[chave], nome)
        return saida

    # -- edição
    def adicionar(self, url, titulo, pasta="barra", indice=None):
        lista = self._lista_de(pasta)
        if lista is None or not _url_navegavel(url):
            return None
        no = {"tipo": "link", "id": uuid.uuid4().hex[:10], "titulo": (titulo or url).strip() or url, "url": url}
        if indice is None:
            lista.append(no)
        else:
            lista.insert(indice, no)
        self._sujo = True
        return no

    def criar_pasta(self, titulo, pai="barra"):
        lista = self._lista_de(pai)
        if lista is None:
            return None
        no = {"tipo": "pasta", "id": uuid.uuid4().hex[:10], "titulo": (titulo or "Nova pasta").strip() or "Nova pasta", "filhos": []}
        lista.append(no)
        self._sujo = True
        return no

    def remover(self, id_):
        no, lista, i = self.achar(id_)
        if no:
            lista.pop(i)
            self._sujo = True
            return True
        return False

    def remover_url(self, url):
        ch = _chave_url(url)
        alvos = [n["id"] for n in self.todos_links() if _chave_url(n["url"]) == ch]
        for i in alvos:
            self.remover(i)
        return bool(alvos)

    def editar(self, id_, titulo=None, url=None):
        no, _l, _i = self.achar(id_)
        if not no:
            return False
        if titulo is not None and titulo.strip():
            no["titulo"] = titulo.strip()
        if url is not None and no["tipo"] == "link" and _url_navegavel(url):
            no["url"] = url
        self._sujo = True
        return True

    def _contem(self, no, id_alvo):
        if no["id"] == id_alvo:
            return True
        return no["tipo"] == "pasta" and any(self._contem(f, id_alvo) for f in no["filhos"])

    def mover(self, id_, novo_pai, indice=None):
        no, lista, i = self.achar(id_)
        destino = self._lista_de(novo_pai)
        if not no or destino is None:
            return False
        if no["tipo"] == "pasta" and self._contem(no, novo_pai):
            return False
        lista.pop(i)
        if indice is None or indice > len(destino):
            destino.append(no)
        else:
            destino.insert(max(0, indice), no)
        self._sujo = True
        return True

    def mover_relativo(self, id_, delta):
        no, lista, i = self.achar(id_)
        if not no:
            return False
        j = i + delta
        if j < 0 or j >= len(lista):
            return False
        lista[i], lista[j] = lista[j], lista[i]
        self._sujo = True
        return True

    # -- importar / exportar (formato HTML padrão dos navegadores)
    def exportar_html(self, caminho):
        linhas = [
            "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            "<TITLE>Bookmarks</TITLE>", "<H1>Bookmarks</H1>", "<DL><p>",
        ]

        def escreve(lista, n):
            ident = "    " * n
            for no in lista:
                if no["tipo"] == "link":
                    linhas.append(f'{ident}<DT><A HREF="{_html.escape(no["url"], quote=True)}">{_html.escape(no["titulo"])}</A>')
                else:
                    linhas.append(f'{ident}<DT><H3>{_html.escape(no["titulo"])}</H3>')
                    linhas.append(f"{ident}<DL><p>")
                    escreve(no["filhos"], n + 1)
                    linhas.append(f"{ident}</DL><p>")

        for chave, nome in _NOMES_RAIZ.items():
            marca = ' PERSONAL_TOOLBAR_FOLDER="true"' if chave == "barra" else ""
            linhas.append(f"    <DT><H3{marca}>{_html.escape(nome)}</H3>")
            linhas.append("    <DL><p>")
            escreve(self.raizes[chave], 2)
            linhas.append("    </DL><p>")
        linhas.append("</DL><p>")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")

    def importar_html(self, caminho, rotulo="Importados"):
        """Importa para 'Outros favoritos' dentro de uma pasta nova. Retorna quantos links entraram."""
        with open(caminho, "r", encoding="utf-8", errors="replace") as f:
            conteudo = f.read()
        p = _ImportadorNetscape()
        p.feed(conteudo)
        total = [0]

        def copia(no):
            if no["tipo"] == "link":
                total[0] += 1
                return {"tipo": "link", "id": uuid.uuid4().hex[:10], "titulo": no["titulo"], "url": no["url"]}
            return {"tipo": "pasta", "id": uuid.uuid4().hex[:10], "titulo": no["titulo"],
                    "filhos": [copia(f) for f in no["filhos"]]}

        filhos = [copia(n) for n in p.raiz["filhos"]]
        if total[0] == 0:
            return 0
        self.raizes["outros"].append({"tipo": "pasta", "id": uuid.uuid4().hex[:10], "titulo": rotulo, "filhos": filhos})
        self._sujo = True
        return total[0]


# -------------------------------------------------------------- configuração
class ConfigNavegador:
    PADRAO = {
        "home": "https://www.youtube.com",
        "busca": "youtube",
        "ao_iniciar": "home",
        "sugestoes_online": True,
        "barra_favoritos": True,
        "zoom_sites": {},
        "sessao": {"urls": [], "ativa": 0},
    }

    def __init__(self, caminho=None):
        self.caminho = caminho or os.path.join(_DIR_NAV, "navegador.json")
        self.dados = json.loads(json.dumps(self.PADRAO))
        salvo = _ler_json(self.caminho, {})
        if isinstance(salvo, dict):
            for k in self.PADRAO:
                if k in salvo and isinstance(salvo[k], type(self.PADRAO[k])):
                    self.dados[k] = salvo[k]
        if self.dados["busca"] not in _MOTORES_BUSCA:
            self.dados["busca"] = "youtube"
        if not _url_navegavel(self.dados["home"]):
            self.dados["home"] = self.PADRAO["home"]

    def get(self, chave):
        return self.dados.get(chave, self.PADRAO.get(chave))

    def set(self, chave, valor):
        self.dados[chave] = valor
        self.salvar()

    def salvar(self):
        return _gravar_json(self.caminho, self.dados)


# ------------------------------------------------------ autocompletar da barra
def _montar_sugestoes(texto, motor, historico, favoritos, abas=(), online=(), max_locais=6):
    """Monta as linhas do menu de sugestões.
    Cada linha: dict(tipo, titulo, url, aba) com tipo em acao|fav|hist|aba|online."""
    t = (texto or "").strip()
    if not t:
        return []
    linhas, vistos = [], set()
    tipo, destino = _interpretar_entrada(t, motor)
    if tipo == "url":
        linhas.append({"tipo": "acao", "titulo": destino, "url": destino, "aba": None})
        vistos.add(_chave_url(destino))
    else:
        nome = _MOTORES_BUSCA.get(motor, _MOTORES_BUSCA["youtube"])[0]
        linhas.append({"tipo": "acao", "titulo": f"{t} — pesquisar no {nome}", "url": destino, "aba": None})

    locais = 0
    for u, tit in favoritos.buscar(t, limite=max_locais):
        ch = _chave_url(u)
        if ch in vistos or locais >= max_locais:
            continue
        vistos.add(ch)
        locais += 1
        linhas.append({"tipo": "fav", "titulo": tit or u, "url": u, "aba": None})
    for u, tit in historico.buscar(t, limite=max_locais * 2):
        ch = _chave_url(u)
        if ch in vistos or locais >= max_locais:
            continue
        vistos.add(ch)
        locais += 1
        linhas.append({"tipo": "hist", "titulo": tit or u, "url": u, "aba": None})
    toks = [x for x in t.lower().split() if x]
    for aba in abas:
        alvo = ((getattr(aba, "url", "") or "") + " " + (getattr(aba, "titulo", "") or "")).lower()
        if getattr(aba, "url", "") and toks and all(x in alvo for x in toks):
            linhas.append({"tipo": "aba", "titulo": aba.titulo or aba.url, "url": aba.url, "aba": aba})
            break
    ja = {l["titulo"].lower() for l in linhas}
    for s in online:
        if s and s.lower() not in ja and s.lower() != t.lower():
            linhas.append({"tipo": "online", "titulo": s, "url": None, "aba": None})
    return linhas


def _completar_inline(texto, historico, favoritos):
    """Completa o que está sendo digitado com um endereço conhecido (ex.: 'you' → 'youtube.com').
    Retorna o texto completo ou None."""
    t = (texto or "").strip().lower()
    if not t or " " in t or "://" in t:
        return None
    t = re.sub(r"^www\.", "", t)
    if not t:
        return None
    melhor = None
    cand = [(u, 1000) for u, _ in favoritos.buscar(t, limite=50)]
    cand += [(u, 0) for u, _ in historico.buscar(t, limite=50)]
    for u, bonus in cand:
        s = _sem_esquema(u)
        if not s.lower().startswith(t):
            continue
        if "/" not in t:
            s = s.split("/", 1)[0]
        pontos = bonus + historico.paginas.get(u, {}).get("n", 0)
        if melhor is None or pontos > melhor[0]:
            melhor = (pontos, s)
    if melhor and melhor[1].lower() != t:
        return melhor[1]
    return None


def _buscar_sugestoes_online(motor, texto, timeout=2.5):
    """Sugestões de busca (formato OpenSearch). Retorna lista de textos; vazia em qualquer erro."""
    try:
        modelo = _URL_SUGESTOES.get(motor, _URL_SUGESTOES["google"])
        req = urllib.request.Request(
            modelo.format(urllib.parse.quote(texto)), headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            bruto = r.read()
            cs = r.headers.get_content_charset() or "utf-8"
        dados = json.loads(bruto.decode(cs, errors="replace"))
        if isinstance(dados, list) and len(dados) > 1 and isinstance(dados[1], list):
            return [str(x) for x in dados[1] if isinstance(x, str)][:6]
    except Exception:
        pass
    return []


# ------------------------------------------------- atalhos de teclado nas páginas
# Dentro do site o foco fica no navegador nativo e o Tk não recebe as teclas. Este
# script captura os atalhos na página e avisa o Python por uma marca temporária no
# endereço (history.replaceState: não cria histórico nem dispara eventos da página).
JS_ATALHOS = r"""
(function(){
  if (window.__yd_atalhos) return; window.__yd_atalhos = true;
  var OK = {aviso_close:1,nova_aba:1,fechar_aba:1,reabrir_aba:1,foco_url:1,favoritar:1,localizar:1,historico:1,
            downloads:1,barra_favoritos:1,favoritos:1,aba_prox:1,aba_ant:1,zoom_mais:1,zoom_menos:1,
            zoom_zero:1,home:1,nova_anonima:1,aba_1:1,aba_2:1,aba_3:1,aba_4:1,aba_5:1,aba_6:1,aba_7:1,aba_8:1,aba_9:1};
  var seq = Math.floor(Math.random() * 100000) * 1000;
  function aplicar(c){
    if (!OK[c]) return;
    seq++;
    try {
      var h = (location.hash || '').replace(/&?__youdown_cmd__=[a-z0-9_]+\.\d+/g, '');
      if (h === '#') h = '';
      var m = '__youdown_cmd__=' + c + '.' + seq;
      var novo = h ? (h + '&' + m) : ('#' + m);
      try { history.replaceState(history.state, '', location.pathname + location.search + novo); }
      catch (e) { location.hash = novo; }
    } catch (e) {}
  }
  function enviar(c){
    if (window !== window.top) { try { window.top.postMessage({__youdown_cmd__: c}, '*'); } catch (e) {} return; }
    aplicar(c);
  }
  /* window.close() dentro do WebView2 DESTRÓI a página (o processo dela termina). Sites de streaming
     chamam isso junto com popups de anúncio. Aqui a chamada vira um aviso e nada é fechado. */
  try { window.close = function(){ try { enviar('aviso_close'); } catch (e) {} }; } catch (e) {}
  if (window === window.top) {
    window.addEventListener('message', function(e){
      try { if (e.data && typeof e.data.__youdown_cmd__ === 'string') aplicar(e.data.__youdown_cmd__); } catch (x) {}
    }, false);
  }
  window.addEventListener('keydown', function(e){
    if (!e.isTrusted) return;
    var k = String(e.key || '').toLowerCase(), c = e.ctrlKey || e.metaKey, s = e.shiftKey, a = e.altKey, cmd = null;
    if (c && !a) {
      if (!s) {
        if (k === 't') cmd = 'nova_aba'; else if (k === 'w') cmd = 'fechar_aba'; else if (k === 'l') cmd = 'foco_url';
        else if (k === 'd') cmd = 'favoritar'; else if (k === 'f') cmd = 'localizar'; else if (k === 'h') cmd = 'historico';
        else if (k === 'j') cmd = 'downloads'; else if (k === '=' || k === '+') cmd = 'zoom_mais';
        else if (k === '-') cmd = 'zoom_menos'; else if (k === '0') cmd = 'zoom_zero';
        else if (k === 'tab' || k === 'pagedown') cmd = 'aba_prox'; else if (k === 'pageup') cmd = 'aba_ant';
        else if (/^[1-9]$/.test(k)) cmd = 'aba_' + k;
      } else {
        if (k === 't') cmd = 'reabrir_aba'; else if (k === 'n') cmd = 'nova_anonima';
        else if (k === 'b') cmd = 'barra_favoritos'; else if (k === 'o') cmd = 'favoritos';
        else if (k === 'tab') cmd = 'aba_ant'; else if (k === '+') cmd = 'zoom_mais';
      }
    } else if (a && !c && !s && k === 'home') cmd = 'home';
    else if (!c && !a && !s && k === 'f6') cmd = 'foco_url';
    if (cmd) { e.preventDefault(); e.stopPropagation(); enviar(cmd); }
  }, true);
  window.addEventListener('wheel', function(e){
    if (e.ctrlKey && e.isTrusted) { e.preventDefault(); enviar(e.deltaY < 0 ? 'zoom_mais' : 'zoom_menos'); }
  }, {passive: false, capture: true});
})();
"""
INIT_JS = ADBLOCK_JS + "\n" + JS_ATALHOS + "\n" + JS_BANNERS   # [Assistir] + módulo de banners

_COMANDOS_JS_OK = {
    "nova_aba", "fechar_aba", "reabrir_aba", "foco_url", "favoritar", "localizar", "historico",
    "downloads", "barra_favoritos", "favoritos", "aba_prox", "aba_ant", "zoom_mais", "zoom_menos",
    "zoom_zero", "home", "nova_anonima", "aviso_close",
} | {f"aba_{i}" for i in range(1, 10)}

# ===========================================================================
# Parte 2: janelas e utilitários de interface do navegador
# ===========================================================================
_DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                "sexta-feira", "sábado", "domingo"]


def _cores():
    """Cores do tema ATUAL (ArduinoTheme.aplicar muda os atributos da classe)."""
    T = ArduinoTheme
    return {
        "fundo": T.BG_SIDEBAR, "campo": T.BG_EDITOR, "texto": T.FG_EDITOR,
        "texto2": T.FG_SIDEBAR, "borda": T.BORDER, "neutro": T.BG_NEUTRO,
        "hover": T.NEUTRO_HOVER, "teal": T.TEAL, "teal_d": T.TEAL_DARK,
        "desab": T.DESABILITADO_FG, "perigo": T.PERIGO_TEXTO,
    }


def _menu_tema(master):
    c = _cores()
    return tk.Menu(master, tearoff=0, bg=c["campo"], fg=c["texto"],
                   activebackground=c["teal"], activeforeground="white",
                   bd=1, relief="solid", font=("Segoe UI", 9))


def _estilo_arvore(master):
    c = _cores()
    st = ttk.Style(master)
    st.configure("Nav.Treeview", background=c["campo"], fieldbackground=c["campo"],
                 foreground=c["texto"], rowheight=24, borderwidth=0)
    st.map("Nav.Treeview", background=[("selected", c["teal"])], foreground=[("selected", "white")])
    st.configure("Nav.Treeview.Heading", background=c["fundo"], foreground=c["texto"], relief="flat")
    return "Nav.Treeview"


def _botao_nav(master, texto, comando, destaque=False, largura=None):
    c = _cores()
    return tk.Button(
        master, text=texto, command=comando, width=largura or 0,
        font=("Segoe UI", 9, "bold" if destaque else "normal"), relief="flat", padx=10, pady=3,
        bg=c["teal"] if destaque else c["neutro"], fg="white" if destaque else c["texto"],
        activebackground=c["teal_d"] if destaque else c["hover"],
        activeforeground="white" if destaque else c["texto"], cursor="hand2",
    )


def _centralizar(win, master, w, h):
    try:
        master.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + max(20, (master.winfo_height() - h) // 3)
    except Exception:
        x, y = 120, 80
    win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")


def _rotulo_dia(ts):
    hoje = time.localtime()
    t = time.localtime(ts)
    d0 = time.mktime((hoje.tm_year, hoje.tm_mon, hoje.tm_mday, 0, 0, 0, 0, 0, -1))
    d1 = time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))
    dias = round((d0 - d1) / 86400)
    if dias == 0:
        return "Hoje"
    if dias == 1:
        return "Ontem"
    return time.strftime("%d/%m/%Y", t) + f" — {_DIAS_SEMANA[t.tm_wday]}"


class _JanelaNav(tk.Toplevel):
    """Base das janelas do navegador: tema, centralização, ESC fecha."""

    def __init__(self, nav, titulo, largura, altura):
        super().__init__(nav.winfo_toplevel())
        self.nav = nav
        self.title(titulo)
        self.c = _cores()
        self.configure(bg=self.c["fundo"])
        self.transient(nav.winfo_toplevel())
        self.minsize(min(largura, 480), min(altura, 320))
        _centralizar(self, nav.winfo_toplevel(), largura, altura)
        self.bind("<Escape>", lambda e: self.destroy())


def _dialogo_editar(parent, titulo_janela, titulo, url=None):
    """Janela modal simples: retorna (titulo, url) ou None se cancelado."""
    c = _cores()
    win = tk.Toplevel(parent)
    win.title(titulo_janela)
    win.configure(bg=c["fundo"])
    win.transient(parent)
    win.resizable(False, False)
    _centralizar(win, parent, 460, 170 if url is not None else 120)
    resultado = {"v": None}
    tk.Label(win, text="Nome", bg=c["fundo"], fg=c["texto"], font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=12, pady=(14, 4))
    e_t = tk.Entry(win, font=("Segoe UI", 10), bg=c["campo"], fg=c["texto"], insertbackground=c["texto"], relief="solid", bd=1)
    e_t.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(14, 4), ipady=3)
    e_t.insert(0, titulo or "")
    e_u = None
    if url is not None:
        tk.Label(win, text="Endereço", bg=c["fundo"], fg=c["texto"], font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=12, pady=4)
        e_u = tk.Entry(win, font=("Segoe UI", 10), bg=c["campo"], fg=c["texto"], insertbackground=c["texto"], relief="solid", bd=1)
        e_u.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=4, ipady=3)
        e_u.insert(0, url)
    win.columnconfigure(1, weight=1)

    def ok(_e=None):
        resultado["v"] = (e_t.get().strip(), e_u.get().strip() if e_u is not None else None)
        win.destroy()

    linha = tk.Frame(win, bg=c["fundo"])
    linha.grid(row=2, column=0, columnspan=2, sticky="e", padx=12, pady=10)
    _botao_nav(linha, "Cancelar", win.destroy).pack(side="right", padx=(6, 0))
    _botao_nav(linha, "Salvar", ok, destaque=True).pack(side="right")
    win.bind("<Return>", ok)
    win.bind("<Escape>", lambda e: win.destroy())
    e_t.focus_set()
    e_t.select_range(0, tk.END)
    win.grab_set()
    parent.wait_window(win)
    return resultado["v"]


# ------------------------------------------------------------------ histórico
class _JanelaHistorico(_JanelaNav):
    def __init__(self, nav):
        super().__init__(nav, "Histórico", 860, 560)
        c = self.c
        barra = tk.Frame(self, bg=c["fundo"])
        barra.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(barra, text="🔎", bg=c["fundo"], fg=c["texto"]).pack(side="left")
        self.var_busca = tk.StringVar()
        self.entry = tk.Entry(barra, textvariable=self.var_busca, font=("Segoe UI", 10), bg=c["campo"],
                              fg=c["texto"], insertbackground=c["texto"], relief="solid", bd=1)
        self.entry.pack(side="left", fill="x", expand=True, padx=6, ipady=3)
        _botao_nav(barra, "Limpar dados…", lambda: nav.dialogo_limpar_dados(self)).pack(side="right", padx=(6, 0))
        _botao_nav(barra, "Excluir selecionados", self.excluir).pack(side="right")

        corpo = tk.Frame(self, bg=c["fundo"])
        corpo.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.arv = ttk.Treeview(corpo, columns=("titulo", "url"), style=_estilo_arvore(self), selectmode="extended")
        self.arv.heading("#0", text="Hora")
        self.arv.heading("titulo", text="Título")
        self.arv.heading("url", text="Endereço")
        self.arv.column("#0", width=150, stretch=False)
        self.arv.column("titulo", width=330)
        self.arv.column("url", width=330)
        sb = ttk.Scrollbar(corpo, orient="vertical", command=self.arv.yview)
        self.arv.configure(yscrollcommand=sb.set)
        self.arv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._mapa = {}
        self._depois = None
        self.var_busca.trace_add("write", lambda *a: self._agendar())
        self.arv.bind("<Double-1>", lambda e: self.abrir())
        self.arv.bind("<Return>", lambda e: self.abrir())
        self.arv.bind("<Delete>", lambda e: self.excluir())
        self.arv.bind("<Button-3>", self._menu)
        self.entry.bind("<Down>", lambda e: (self.arv.focus_set(), "break")[1])
        self.recarregar()
        self.entry.focus_set()

    def _agendar(self):
        if self._depois:
            self.after_cancel(self._depois)
        self._depois = self.after(200, self.recarregar)

    def recarregar(self):
        self._depois = None
        self.arv.delete(*self.arv.get_children())
        self._mapa = {}
        grupos = {}
        n = 0
        for ts, url, tit in self.nav.historico.lista(self.var_busca.get(), limite=2000):
            rot = _rotulo_dia(ts)
            if rot not in grupos:
                grupos[rot] = self.arv.insert("", "end", text=rot, open=True, values=("", ""))
            n += 1
            iid = f"v{n}"
            self._mapa[iid] = (ts, url)
            self.arv.insert(grupos[rot], "end", iid=iid, text=time.strftime("%H:%M", time.localtime(ts)),
                            values=(tit or "(sem título)", url))
        if not self._mapa:
            self.arv.insert("", "end", text="Nenhum resultado" if self.var_busca.get().strip() else "O histórico está vazio", values=("", ""))

    def _selecionados(self):
        return [self._mapa[i] for i in self.arv.selection() if i in self._mapa]

    def abrir(self, nova_aba=False):
        sel = self._selecionados()
        if not sel:
            return
        if nova_aba:
            self.nav.nova_aba(sel[0][1])
        else:
            self.nav.navegar_para(sel[0][1])

    def excluir(self):
        sel = self._selecionados()
        for ts, url in sel:
            self.nav.historico.remover_visita(ts, url)
        if sel:
            self.nav.historico.salvar()
            self.recarregar()

    def _menu(self, ev):
        iid = self.arv.identify_row(ev.y)
        if iid not in self._mapa:
            return
        if iid not in self.arv.selection():
            self.arv.selection_set(iid)
        m = _menu_tema(self)
        m.add_command(label="Abrir", command=self.abrir)
        m.add_command(label="Abrir em nova aba", command=lambda: self.abrir(True))
        m.add_command(label="Copiar endereço", command=self._copiar)
        m.add_separator()
        m.add_command(label="Excluir do histórico", command=self.excluir)
        m.tk_popup(ev.x_root, ev.y_root)

    def _copiar(self):
        sel = self._selecionados()
        if sel:
            self.clipboard_clear()
            self.clipboard_append(sel[0][1])


# ------------------------------------------------------------------ favoritos
class _JanelaFavoritos(_JanelaNav):
    def __init__(self, nav):
        super().__init__(nav, "Gerenciador de favoritos", 820, 560)
        c = self.c
        barra = tk.Frame(self, bg=c["fundo"])
        barra.pack(fill="x", padx=10, pady=(10, 6))
        for txt, cmd in (("Nova pasta", self.nova_pasta), ("Editar…", self.editar), ("Excluir", self.excluir),
                         ("▲", lambda: self.mover(-1)), ("▼", lambda: self.mover(1))):
            _botao_nav(barra, txt, cmd).pack(side="left", padx=(0, 4))
        _botao_nav(barra, "Exportar…", self.exportar).pack(side="right", padx=(4, 0))
        _botao_nav(barra, "Importar…", self.importar).pack(side="right")

        corpo = tk.Frame(self, bg=c["fundo"])
        corpo.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.arv = ttk.Treeview(corpo, columns=("url",), style=_estilo_arvore(self), selectmode="browse")
        self.arv.heading("#0", text="Nome")
        self.arv.heading("url", text="Endereço")
        self.arv.column("#0", width=300)
        self.arv.column("url", width=420)
        sb = ttk.Scrollbar(corpo, orient="vertical", command=self.arv.yview)
        self.arv.configure(yscrollcommand=sb.set)
        self.arv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.arv.bind("<Double-1>", lambda e: self.abrir())
        self.arv.bind("<Delete>", lambda e: self.excluir())
        self.arv.bind("<Button-3>", self._menu)
        self.recarregar()

    def recarregar(self, manter=None):
        fav = self.nav.favoritos
        self.arv.delete(*self.arv.get_children())

        def preenche(pai, lista):
            for n in lista:
                if n["tipo"] == "pasta":
                    iid = self.arv.insert(pai, "end", iid=n["id"], text="📁 " + n["titulo"], open=True, values=("",))
                    preenche(iid, n["filhos"])
                else:
                    self.arv.insert(pai, "end", iid=n["id"], text="⭐ " + n["titulo"], values=(n["url"],))
        for chave, nome in _NOMES_RAIZ.items():
            raiz = self.arv.insert("", "end", iid=chave, text="📂 " + nome, open=True, values=("",))
            preenche(raiz, fav.raizes[chave])
        if manter and self.arv.exists(manter):
            self.arv.selection_set(manter)
            self.arv.see(manter)

    def _alterou(self, manter=None):
        self.nav.favoritos.salvar()
        self.recarregar(manter)
        self.nav._favoritos_mudaram()

    def _sel(self):
        s = self.arv.selection()
        return s[0] if s else None

    def _no(self, iid):
        if iid in _NOMES_RAIZ:
            return None
        return self.nav.favoritos.achar(iid)[0]

    def _pai_para_novo(self):
        iid = self._sel()
        if iid in _NOMES_RAIZ:
            return iid
        no = self._no(iid) if iid else None
        if no and no["tipo"] == "pasta":
            return no["id"]
        if no:
            pai = self.arv.parent(iid)
            return pai or "barra"
        return "barra"

    def nova_pasta(self):
        r = _dialogo_editar(self, "Nova pasta", "Nova pasta")
        if r and r[0]:
            no = self.nav.favoritos.criar_pasta(r[0], self._pai_para_novo())
            self._alterou(no["id"] if no else None)

    def editar(self):
        iid = self._sel()
        no = self._no(iid) if iid else None
        if not no:
            return
        r = _dialogo_editar(self, "Editar", no["titulo"], no.get("url") if no["tipo"] == "link" else None)
        if r:
            self.nav.favoritos.editar(iid, titulo=r[0], url=r[1])
            self._alterou(iid)

    def excluir(self):
        iid = self._sel()
        no = self._no(iid) if iid else None
        if not no:
            return
        if no["tipo"] == "pasta" and no["filhos"]:
            if not messagebox.askyesno("Excluir pasta", f"Excluir a pasta “{no['titulo']}” e tudo que há nela?", parent=self):
                return
        self.nav.favoritos.remover(iid)
        self._alterou()

    def mover(self, delta):
        iid = self._sel()
        if iid and self._no(iid) and self.nav.favoritos.mover_relativo(iid, delta):
            self._alterou(iid)

    def abrir(self, nova_aba=False):
        no = self._no(self._sel() or "")
        if no and no["tipo"] == "link":
            (self.nav.nova_aba if nova_aba else self.nav.navegar_para)(no["url"])

    def _menu(self, ev):
        iid = self.arv.identify_row(ev.y)
        if not iid:
            return
        self.arv.selection_set(iid)
        no = self._no(iid)
        m = _menu_tema(self)
        if no and no["tipo"] == "link":
            m.add_command(label="Abrir", command=self.abrir)
            m.add_command(label="Abrir em nova aba", command=lambda: self.abrir(True))
            m.add_separator()
        if no:
            m.add_command(label="Editar…", command=self.editar)
            sub = _menu_tema(m)
            for pid, caminho in self.nav.favoritos.listar_pastas():
                sub.add_command(label=caminho, command=lambda p=pid: self._mover_para(iid, p))
            m.add_cascade(label="Mover para", menu=sub)
            m.add_command(label="Excluir", command=self.excluir)
            m.add_separator()
        m.add_command(label="Nova pasta", command=self.nova_pasta)
        m.tk_popup(ev.x_root, ev.y_root)

    def _mover_para(self, iid, pasta):
        if self.nav.favoritos.mover(iid, pasta):
            self._alterou(iid)

    def exportar(self):
        caminho = filedialog.asksaveasfilename(parent=self, title="Exportar favoritos", defaultextension=".html",
                                               initialfile="favoritos.html", filetypes=[("Favoritos (HTML)", "*.html")])
        if caminho:
            try:
                self.nav.favoritos.exportar_html(caminho)
                messagebox.showinfo("Exportar", "Favoritos exportados com sucesso.", parent=self)
            except Exception as e:
                messagebox.showerror("Exportar", f"Não foi possível exportar:\n{e}", parent=self)

    def importar(self):
        caminho = filedialog.askopenfilename(parent=self, title="Importar favoritos",
                                             filetypes=[("Favoritos (HTML)", "*.html *.htm"), ("Todos", "*.*")])
        if not caminho:
            return
        try:
            n = self.nav.favoritos.importar_html(caminho, rotulo="Importados em " + time.strftime("%d/%m/%Y"))
        except Exception as e:
            messagebox.showerror("Importar", f"Não foi possível importar:\n{e}", parent=self)
            return
        if n:
            self._alterou()
            messagebox.showinfo("Importar", f"{n} favoritos importados para “Outros favoritos”.", parent=self)
        else:
            messagebox.showwarning("Importar", "Nenhum favorito encontrado nesse arquivo.", parent=self)


# ------------------------------------------------------------------ downloads
class _JanelaDownloads(_JanelaNav):
    def __init__(self, nav):
        super().__init__(nav, "Downloads", 760, 420)
        c = self.c
        barra = tk.Frame(self, bg=c["fundo"])
        barra.pack(fill="x", padx=10, pady=(10, 6))
        _botao_nav(barra, "Abrir arquivo", self.abrir).pack(side="left", padx=(0, 4))
        _botao_nav(barra, "Mostrar na pasta", self.pasta).pack(side="left", padx=(0, 4))
        _botao_nav(barra, "Limpar lista", self.limpar).pack(side="right")
        corpo = tk.Frame(self, bg=c["fundo"])
        corpo.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.arv = ttk.Treeview(corpo, columns=("estado", "destino"), style=_estilo_arvore(self), selectmode="browse")
        self.arv.heading("#0", text="Arquivo")
        self.arv.heading("estado", text="Estado")
        self.arv.heading("destino", text="Salvo em")
        self.arv.column("#0", width=230)
        self.arv.column("estado", width=100, stretch=False)
        self.arv.column("destino", width=380)
        self.arv.pack(fill="both", expand=True)
        self.arv.bind("<Double-1>", lambda e: self.abrir())
        self._ciclo()

    def _ciclo(self):
        try:
            sel = self.arv.selection()
            self.arv.delete(*self.arv.get_children())
            nomes = {"baixando": "⏳ Baixando", "concluido": "✔ Concluído", "falhou": "✖ Falhou"}
            for d in reversed(self.nav.downloads):
                self.arv.insert("", "end", iid=str(d["id"]), text=d["nome"],
                                values=(nomes.get(d["estado"], d["estado"]), d["destino"]))
            if sel and self.arv.exists(sel[0]):
                self.arv.selection_set(sel[0])
            self._after = self.after(1000, self._ciclo)
        except tk.TclError:
            pass

    def _atual(self):
        s = self.arv.selection()
        for d in self.nav.downloads:
            if s and str(d["id"]) == s[0]:
                return d
        return None

    def abrir(self):
        d = self._atual()
        if d and d["estado"] == "concluido" and os.path.exists(d["destino"]):
            self.nav._abrir_no_sistema(d["destino"])

    def pasta(self):
        d = self._atual()
        if d:
            self.nav._mostrar_na_pasta(d["destino"])

    def limpar(self):
        self.nav.downloads[:] = [d for d in self.nav.downloads if d["estado"] == "baixando"]


# --------------------------------------------------------------- configurações
class _JanelaConfig(_JanelaNav):
    def __init__(self, nav):
        super().__init__(nav, "Configurações do navegador", 520, 430)
        c, cfg = self.c, nav.cfg
        corpo = tk.Frame(self, bg=c["fundo"])
        corpo.pack(fill="both", expand=True, padx=16, pady=14)

        def rotulo(txt, pady=(10, 3)):
            tk.Label(corpo, text=txt, bg=c["fundo"], fg=c["texto"], font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=pady)

        rotulo("Página inicial", (0, 3))
        self.e_home = tk.Entry(corpo, font=("Segoe UI", 10), bg=c["campo"], fg=c["texto"], insertbackground=c["texto"], relief="solid", bd=1)
        self.e_home.pack(fill="x", ipady=3)
        self.e_home.insert(0, cfg.get("home"))

        rotulo("Mecanismo de busca da barra de endereço")
        self.nomes = {v[0]: k for k, v in _MOTORES_BUSCA.items()}
        self.cb = ttk.Combobox(corpo, values=list(self.nomes), state="readonly", font=("Segoe UI", 10))
        self.cb.set(_MOTORES_BUSCA[cfg.get("busca")][0])
        self.cb.pack(fill="x")
        tk.Label(corpo, text="Dica: digite “yt”, “g”, “ddg” ou “bing” antes do texto para escolher na hora.",
                 bg=c["fundo"], fg=c["texto2"], font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 0))

        rotulo("Ao iniciar")
        self.var_ini = tk.StringVar(value=cfg.get("ao_iniciar"))
        for val, txt in (("home", "Abrir a página inicial"), ("continuar", "Continuar de onde parei (reabrir as abas)")):
            tk.Radiobutton(corpo, text=txt, variable=self.var_ini, value=val, bg=c["fundo"], fg=c["texto"],
                           selectcolor=c["campo"], activebackground=c["fundo"], activeforeground=c["texto"],
                           font=("Segoe UI", 9)).pack(anchor="w")

        rotulo("Barra de endereço")
        self.var_sug = tk.BooleanVar(value=bool(cfg.get("sugestoes_online")))
        tk.Checkbutton(corpo, text="Mostrar sugestões de busca da internet (envia o que você digita ao buscador)",
                       variable=self.var_sug, bg=c["fundo"], fg=c["texto"], selectcolor=c["campo"],
                       activebackground=c["fundo"], activeforeground=c["texto"], font=("Segoe UI", 9),
                       wraplength=460, justify="left").pack(anchor="w")
        self.var_barra = tk.BooleanVar(value=bool(cfg.get("barra_favoritos")))
        tk.Checkbutton(corpo, text="Mostrar a barra de favoritos", variable=self.var_barra, bg=c["fundo"],
                       fg=c["texto"], selectcolor=c["campo"], activebackground=c["fundo"],
                       activeforeground=c["texto"], font=("Segoe UI", 9)).pack(anchor="w")

        rodape = tk.Frame(self, bg=c["fundo"])
        rodape.pack(fill="x", padx=16, pady=(0, 14))
        _botao_nav(rodape, "Limpar dados de navegação…", lambda: nav.dialogo_limpar_dados(self)).pack(side="left")
        _botao_nav(rodape, "Cancelar", self.destroy).pack(side="right", padx=(6, 0))
        _botao_nav(rodape, "Salvar", self.salvar, destaque=True).pack(side="right")

    def salvar(self):
        home = self.e_home.get().strip()
        kind, url = _interpretar_entrada(home)
        if kind != "url" or not _url_navegavel(url):
            messagebox.showwarning("Página inicial", "Informe um endereço válido, por exemplo: https://www.youtube.com", parent=self)
            return
        cfg = self.nav.cfg
        cfg.dados["home"] = url
        cfg.dados["busca"] = self.nomes.get(self.cb.get(), "youtube")
        cfg.dados["ao_iniciar"] = self.var_ini.get()
        cfg.dados["sugestoes_online"] = bool(self.var_sug.get())
        mostrar = bool(self.var_barra.get())
        mudou_barra = mostrar != bool(cfg.get("barra_favoritos"))
        cfg.dados["barra_favoritos"] = mostrar
        cfg.salvar()
        if mudou_barra:
            self.nav._aplicar_visibilidade_barra()
        self.destroy()


# -------------------------------------------------------------- limpar dados
class _JanelaLimparDados(tk.Toplevel):
    PERIODOS = [("Última hora", 3600), ("Últimas 24 horas", 86400), ("Últimos 7 dias", 7 * 86400),
                ("Últimos 30 dias", 30 * 86400), ("Todo o período", None)]

    def __init__(self, nav, pai):
        super().__init__(pai)
        c = _cores()
        self.nav = nav
        self.title("Limpar dados de navegação")
        self.configure(bg=c["fundo"])
        self.transient(pai)
        self.resizable(False, False)
        _centralizar(self, pai, 480, 330)
        tk.Label(self, text="Período", bg=c["fundo"], fg=c["texto"], font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=16, pady=(14, 3))
        self.cb = ttk.Combobox(self, values=[p[0] for p in self.PERIODOS], state="readonly", font=("Segoe UI", 10))
        self.cb.current(len(self.PERIODOS) - 1)
        self.cb.pack(fill="x", padx=16)
        self.v_hist = tk.BooleanVar(value=True)
        self.v_cook = tk.BooleanVar(value=False)
        estilo = dict(bg=c["fundo"], fg=c["texto"], selectcolor=c["campo"], activebackground=c["fundo"],
                      activeforeground=c["texto"], font=("Segoe UI", 9), justify="left", wraplength=430)
        tk.Checkbutton(self, text="Histórico de navegação", variable=self.v_hist, **estilo).pack(anchor="w", padx=16, pady=(12, 0))
        tk.Checkbutton(self, text="Cookies, cache e dados dos sites\n(apaga tudo, de todo o período, e desconecta você das suas contas)",
                       variable=self.v_cook, **estilo).pack(anchor="w", padx=16, pady=(6, 0))
        tk.Label(self, text="Favoritos e senhas salvas pelo site nunca são tocados por esta janela.\n"
                            "Abas anônimas não deixam histórico.",
                 bg=c["fundo"], fg=c["texto2"], font=("Segoe UI", 8), justify="left").pack(anchor="w", padx=16, pady=(12, 0))
        rodape = tk.Frame(self, bg=c["fundo"])
        rodape.pack(side="bottom", fill="x", padx=16, pady=14)
        _botao_nav(rodape, "Cancelar", self.destroy).pack(side="right", padx=(6, 0))
        _botao_nav(rodape, "Limpar dados", self.executar, destaque=True).pack(side="right")
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()

    def executar(self):
        seg = dict(self.PERIODOS)[self.cb.get()]
        feito = []
        if self.v_hist.get():
            self.nav.historico.limpar(None if seg is None else time.time() - seg)
            self.nav.historico.salvar(forcar=True)
            feito.append("histórico")
        if self.v_cook.get():
            if self.nav._limpar_dados_sites():
                feito.append("cookies e dados dos sites")
        if self.nav.on_info:
            self.nav.on_info("🧹 Dados limpos: " + (", ".join(feito) if feito else "nada selecionado"))
        self.destroy()


# ------------------------------------------------------ pop-up da estrela ⭐
class _PopupFavorito(tk.Toplevel):
    def __init__(self, nav, url, titulo, novo):
        super().__init__(nav.winfo_toplevel())
        c = _cores()
        self.nav, self.url = nav, url
        self.title("Favorito adicionado" if novo else "Editar favorito")
        self.configure(bg=c["fundo"])
        self.transient(nav.winfo_toplevel())
        self.resizable(False, False)
        _centralizar(self, nav.winfo_toplevel(), 420, 190)
        tk.Label(self, text="⭐ Favorito salvo" if novo else "⭐ Editar favorito", bg=c["fundo"], fg=c["texto"],
                 font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6))
        tk.Label(self, text="Nome", bg=c["fundo"], fg=c["texto"], font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=14, pady=4)
        self.e_nome = tk.Entry(self, font=("Segoe UI", 10), bg=c["campo"], fg=c["texto"], insertbackground=c["texto"], relief="solid", bd=1)
        self.e_nome.grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=4, ipady=3)
        self.e_nome.insert(0, titulo)
        tk.Label(self, text="Pasta", bg=c["fundo"], fg=c["texto"], font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", padx=14, pady=4)
        self.pastas = nav.favoritos.listar_pastas()
        self.cb = ttk.Combobox(self, values=[p[1] for p in self.pastas], state="readonly", font=("Segoe UI", 9))
        no = nav.favoritos.achar_por_url(url)
        self.cb.current(self._indice_pasta(no))
        self.cb.grid(row=2, column=1, sticky="ew", padx=(0, 14), pady=4)
        self.columnconfigure(1, weight=1)
        linha = tk.Frame(self, bg=c["fundo"])
        linha.grid(row=3, column=0, columnspan=2, sticky="e", padx=14, pady=12)
        _botao_nav(linha, "Remover", self.remover).pack(side="left", padx=(0, 6))
        _botao_nav(linha, "Concluído", self.concluir, destaque=True).pack(side="left")
        self.bind("<Return>", lambda e: self.concluir())
        self.bind("<Escape>", lambda e: self.concluir())
        self.e_nome.focus_set()
        self.e_nome.select_range(0, tk.END)

    def _indice_pasta(self, no):
        if not no:
            return 0
        _n, lista, _i = self.nav.favoritos.achar(no["id"])
        for idx, (pid, _c) in enumerate(self.pastas):
            if self.nav.favoritos._lista_de(pid) is lista:
                return idx
        return 0

    def concluir(self):
        fav = self.nav.favoritos
        no = fav.achar_por_url(self.url)
        if no:
            fav.editar(no["id"], titulo=self.e_nome.get().strip() or no["titulo"])
            destino = self.pastas[self.cb.current()][0]
            if fav._lista_de(destino) is not fav.achar(no["id"])[1]:
                fav.mover(no["id"], destino)
        fav.salvar()
        self.nav._favoritos_mudaram()
        self.destroy()

    def remover(self):
        self.nav.favoritos.remover_url(self.url)
        self.nav.favoritos.salvar()
        self.nav._favoritos_mudaram()
        self.destroy()

# ===========================================================================
# Parte 3: barra de endereço com autocompletar, abas e o navegador em si
# ===========================================================================
import tkinter.font as tkfont
import webbrowser

_ICONES_SUG = {"acao": "🌐", "fav": "⭐", "hist": "🕘", "aba": "🗂", "online": "🔍"}
_PASSOS_ZOOM = [0.25, 0.33, 0.5, 0.67, 0.75, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0]
_TECLAS_IGNORADAS_SUG = {
    "Up", "Down", "Return", "KP_Enter", "Escape", "Tab", "ISO_Left_Tab", "Shift_L", "Shift_R",
    "Control_L", "Control_R", "Alt_L", "Alt_R", "Left", "Right", "Home", "End", "Caps_Lock",
    "Meta_L", "Super_L", "Menu", "Prior", "Next", "F5", "F6", "F11", "F12",
}


class _Omnibox:
    """Menu de sugestões da barra de endereço: favoritos, histórico, abas abertas,
    sugestões de busca e completar-automático dentro do próprio campo."""

    def __init__(self, nav):
        self.nav = nav
        self.entry = nav.url_entry
        self.win = None
        self.lista = None
        self.itens = []
        self.sel = -1
        self.digitado = ""
        self._depois_online = None
        self._fila = queue.Queue()
        self._cache = {}
        self._pendentes = 0
        self._polling = False

    # -- ciclo de vida
    def aberto(self):
        return self.win is not None

    def fechar(self):
        if self.win is not None:
            try:
                self.win.destroy()
            except Exception:
                pass
        self.win = self.lista = None
        self.itens = []
        self.sel = -1

    def ao_desfocar(self):
        def checa():
            try:
                if self.nav.focus_get() is not self.entry:
                    self.fechar()
            except Exception:
                self.fechar()
        self.nav.after(220, checa)

    # -- digitação
    def ao_soltar_tecla(self, ev):
        if ev.keysym in _TECLAS_IGNORADAS_SUG:
            return
        # Ctrl+tecla (atalhos) não é digitação
        if (ev.state & 0x4) and ev.keysym.lower() not in ("v", "x"):
            return
        texto = self.entry.get()
        self.digitado = texto
        self.sel = -1
        self.atualizar(texto, inline=ev.keysym not in ("BackSpace", "Delete"))

    def atualizar(self, texto, inline=True):
        nav = self.nav
        t = texto.strip()
        if not t:
            self.fechar()
            return
        online = self._cache.get(t, [])
        self.itens = _montar_sugestoes(
            texto, nav.cfg.get("busca"), nav.historico, nav.favoritos, nav.abas, online)
        self._mostrar()
        if inline:
            self._inline(texto)
        self._pedir_online(t)

    def _inline(self, texto):
        try:
            if self.entry.index(tk.INSERT) != len(texto):
                return
            comp = _completar_inline(texto, self.nav.historico, self.nav.favoritos)
            if comp and comp.lower().startswith(texto.strip().lower()) and len(texto.strip()) == len(texto):
                self.entry.insert(tk.END, comp[len(texto):])
                self.entry.select_range(len(texto), tk.END)
                self.entry.icursor(tk.END)
        except Exception:
            pass

    # -- janela de sugestões
    def _texto_linha(self, l):
        ic = _ICONES_SUG.get(l["tipo"], "•")
        if l["tipo"] in ("fav", "hist"):
            t = f'{l["titulo"]}  —  {_sem_esquema(l["url"])}'
        elif l["tipo"] == "aba":
            t = f'Ir para a aba: {l["titulo"]}'
        else:
            t = l["titulo"]
        t = t if len(t) <= 120 else t[:119] + "…"
        return f"  {ic}   {t}"

    def _mostrar(self):
        if not self.itens:
            self.fechar()
            return
        c = _cores()
        caixa = self.nav.caixa_url
        if self.win is None:
            self.win = tk.Toplevel(self.nav.winfo_toplevel())
            self.win.overrideredirect(True)
            try:
                self.win.attributes("-topmost", True)
            except Exception:
                pass
            self.lista = tk.Listbox(
                self.win, font=("Segoe UI", 10), activestyle="none", bd=0, relief="flat",
                highlightthickness=1, highlightbackground=c["borda"], highlightcolor=c["borda"],
                exportselection=False, takefocus=0, bg=c["campo"], fg=c["texto"],
                selectbackground=c["teal"], selectforeground="white",
            )
            self.lista.pack(fill="both", expand=True)
            self.lista.bind("<ButtonPress-1>", self._clicou)
        self.lista.delete(0, tk.END)
        for l in self.itens:
            self.lista.insert(tk.END, self._texto_linha(l))
        if 0 <= self.sel < len(self.itens):
            self.lista.selection_set(self.sel)
        try:
            alt_linha = tkfont.Font(font=self.lista.cget("font")).metrics("linespace") + 6
            n = min(len(self.itens), 10)
            self.lista.configure(height=n)
            self.nav.update_idletasks()
            x, y = caixa.winfo_rootx(), caixa.winfo_rooty() + caixa.winfo_height()
            self.win.geometry(f"{max(caixa.winfo_width(), 320)}x{n * alt_linha + 4}+{x}+{y}")
            self.win.lift()
        except Exception:
            pass

    def _clicou(self, ev):
        try:
            idx = self.lista.nearest(ev.y)
            if 0 <= idx < len(self.itens):
                self.escolher(self.itens[idx])
        except Exception:
            pass
        return "break"

    # -- navegação por teclado
    def mover(self, delta):
        if not self.aberto():
            texto = self.entry.get()
            if texto.strip() and delta > 0:
                self.digitado = texto
                self.atualizar(texto, inline=False)
            return "break"
        n = len(self.itens)
        novo = self.sel + delta
        if novo < -1:
            novo = n - 1
        elif novo >= n:
            novo = -1
        self.sel = novo
        self.lista.selection_clear(0, tk.END)
        if novo >= 0:
            self.lista.selection_set(novo)
            self.lista.see(novo)
            l = self.itens[novo]
            texto = l["url"] if (l["tipo"] in ("fav", "hist", "aba") and l["url"]) else (
                l["titulo"].split(" — pesquisar")[0] if l["tipo"] == "acao" and not _url_navegavel(l["titulo"]) else l["titulo"])
        else:
            texto = self.digitado
        self.entry.delete(0, tk.END)
        self.entry.insert(0, texto)
        self.entry.icursor(tk.END)
        return "break"

    def confirmar(self):
        if self.aberto() and 0 <= self.sel < len(self.itens):
            return self.itens[self.sel]
        return None

    def escolher(self, linha):
        self.fechar()
        self.nav._abrir_sugestao(linha)

    def aceitar_inline(self):
        """Tab/→ no fim do campo: aceita o trecho completado automaticamente."""
        try:
            if self.entry.selection_present():
                self.entry.selection_clear()
                self.entry.icursor(tk.END)
                self.digitado = self.entry.get()
                self.atualizar(self.digitado, inline=False)
                return "break"
        except Exception:
            pass
        return None

    # -- sugestões de busca da internet (em segundo plano)
    def _pedir_online(self, t):
        nav = self.nav
        if self._depois_online:
            try:
                nav.after_cancel(self._depois_online)
            except Exception:
                pass
            self._depois_online = None
        if not nav.cfg.get("sugestoes_online") or len(t) < 2 or t in self._cache:
            return
        if _interpretar_entrada(t, nav.cfg.get("busca"))[0] != "busca":
            return
        if nav.aba_ativa is not None and nav.aba_ativa.anonima:
            return
        self._depois_online = nav.after(280, lambda: self._disparar(t))

    def _disparar(self, t):
        self._depois_online = None
        motor = self.nav.cfg.get("busca")
        self._pendentes += 1

        def trabalho():
            lista = _buscar_sugestoes_online(motor, t)
            self._fila.put((t, lista))
        threading.Thread(target=trabalho, daemon=True).start()
        if not self._polling:
            self._polling = True
            self.nav.after(150, self._poll)

    def _poll(self):
        try:
            while True:
                t, lista = self._fila.get_nowait()
                self._pendentes = max(0, self._pendentes - 1)
                if len(self._cache) > 60:
                    self._cache.clear()
                self._cache[t] = lista
                if (self.aberto() and self.sel < 0 and self.digitado.strip() == t
                        and self.entry.get().strip().lower().startswith(t.lower())):
                    self.atualizar(self.digitado, inline=False)
        except queue.Empty:
            pass
        except Exception:
            pass
        if self._pendentes > 0:
            self.nav.after(150, self._poll)
        else:
            self._polling = False


class _Aba:
    """Estado de uma aba. O WebView só é criado quando a aba é mostrada pela 1ª vez."""
    _contador = 0

    def __init__(self, url=None, anonima=False):
        _Aba._contador += 1
        self.id = _Aba._contador
        self.url = url or ""
        self.url_inicial = url
        self.inicio = url is None
        self.titulo = ""
        self.anonima = anonima
        self.frame = None
        self.webview = None
        self.lbl_espera = None
        self.criando = False
        self.fechada = False
        self.carregando = False
        self.carga_t = 0.0
        self.ref_nav = self.url
        self.nav_livre = None
        self.ult_aviso = ("", 0.0)
        self.zoom = 1.0
        self.zoom_aplicado = None
        self.hist_after = None
        self.cmd_seq = 0
        self.chip = None
        self.url_anterior = ""
        self.ultimo_ok = 0.0
        self.bat_pend = 0.0
        self.carga_ok_t = 0.0
        self.recuperacoes = []


class NavegadorSimples(tk.Frame):
    """Navegador embutido: abas, histórico, favoritos, autocompletar, zoom por site,
    localizar na página, downloads e abas anônimas. Mantém a API usada pelo app
    (webview, top, container, url_atual, fechar, abrir_url_direta, ...)."""

    MAX_ABAS = 40

    def __init__(self, master, on_url_mudou, on_capturar_url, on_fullscreen=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_url_mudou = on_url_mudou
        self.on_capturar_url = on_capturar_url
        self.on_fullscreen = on_fullscreen
        self.on_info = None
        self.on_site_digitado = None      # [Assistir] chamado quando o usuário digita/escolhe um endereço
        self.menu_extra = None            # [Assistir] função que devolve itens extras para o menu ⋮
        self.bloquear_downloads = False   # [Assistir] opção "só assistir"
        self.editando_url = False
        self.navegador_em_fs = False
        self._fs_disparado_por_site = False
        self._fs_ultimo_seq = 0
        self._ignorar_fs_ate = 0

        self.historico = HistoricoNavegador()
        self.favoritos = FavoritosNavegador()
        self.cfg = ConfigNavegador()
        self.downloads = []
        self._dl_id = 0
        self.abas = []
        self.aba_ativa = None
        self._fechadas = []
        self._sessao_normal = None
        self._sessao_anonima = None
        self._janelas = {}
        self._tema_regs = []
        self._spin_i = 0
        self._spin_after = None
        self._salvar_after = None
        self._layout_abas_after = None
        self._layout_fav_after = None
        self._ult_cmd = {}
        self._PLE = None
        self._aviso_ativo_logado = False
        self.barra_busca = None
        self._itens_fav = []
        self._var_barra = tk.BooleanVar(value=bool(self.cfg.get("barra_favoritos")))

        # REGRA DE OURO: os hooks SÍNCRONOS do tkwry (on_navigation, on_new_window, on_download) rodam
        # DENTRO do laço de eventos do Tk. Neles é PROIBIDO tocar no Tk (log da tela, after, widgets):
        # isso derruba o Python com "PyEval_RestoreThread ... GIL is released". Eles só decidem e
        # colocam os efeitos nesta fila, que um temporizador normal do Tk esvazia depois.
        self._fila_ui = queue.Queue()
        self._instalar_diagnostico()
        self._montar_ui()
        self.omni = _Omnibox(self)
        self._montar_eventos_url()
        self._montar_atalhos()
        self.reaplicar_tema()
        self.after(60, self._drenar_fila_ui)
        self.after(250, self._iniciar)

    # ------------------------------------------------------------ compatibilidade
    @property
    def webview(self):
        a = self.aba_ativa
        return a.webview if a else None

    @property
    def url_atual(self):
        a = self.aba_ativa
        return a.url if a else ""

    @url_atual.setter
    def url_atual(self, v):
        if self.aba_ativa is not None:
            self.aba_ativa.url = v

    def _escrever_log(self, msg):
        """Grava em ~/.youdown/navegador.log (fica mesmo se o programa fechar de repente)."""
        try:
            os.makedirs(_DIR_NAV, exist_ok=True)
            caminho = os.path.join(_DIR_NAV, "navegador.log")
            if os.path.exists(caminho) and os.path.getsize(caminho) > 512 * 1024:
                os.replace(caminho, caminho + ".1")
            with open(caminho, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg).replace("\n", "\n    ") + "\n")
        except Exception:
            pass

    def _log(self, msg):
        self._escrever_log(msg)
        if self.on_info:
            try:
                self.on_info(msg)
            except Exception:
                pass

    def _log_seguro(self, msg):
        """Para uso DENTRO dos hooks síncronos do tkwry: grava no arquivo agora e leva o texto
        para a tela depois (sem tocar no Tk)."""
        self._escrever_log(msg)
        self._fila_ui.put(("log", msg))

    def _drenar_fila_ui(self):
        try:
            while True:
                item = self._fila_ui.get_nowait()
                try:
                    if item[0] == "log":
                        if self.on_info:
                            self.on_info(item[1])
                    elif item[0] == "navegar":
                        self.navegar_para(item[1], item[2])
                    elif item[0] == "nova_aba":
                        self.nova_aba(item[1], ao_lado=True, anonima=item[2])
                except Exception as e:
                    self._escrever_log(f"erro ao aplicar efeito de interface {item[0]}: {e}")
        except queue.Empty:
            pass
        finally:
            self.after(60, self._drenar_fila_ui)

    def _instalar_diagnostico(self):
        """Registra falhas nativas (crash) e exceções de callbacks do Tk em arquivos."""
        global _FH_ARQUIVO
        try:
            import faulthandler
            if _FH_ARQUIVO is None:
                os.makedirs(_DIR_NAV, exist_ok=True)
                _FH_ARQUIVO = open(os.path.join(_DIR_NAV, "crash.log"), "a", buffering=1, encoding="utf-8")
                _FH_ARQUIVO.write(time.strftime("\n=== %Y-%m-%d %H:%M:%S sessão iniciada ===\n"))
                faulthandler.enable(file=_FH_ARQUIVO, all_threads=True)
        except Exception:
            pass
        try:
            import traceback
            raiz = self.winfo_toplevel()
            original = raiz.report_callback_exception

            def relatar(exc, val, tb):
                self._escrever_log("EXCEÇÃO no Tk:\n" + "".join(traceback.format_exception(exc, val, tb)))
                try:
                    original(exc, val, tb)
                except Exception:
                    pass
            raiz.report_callback_exception = relatar
        except Exception:
            pass

    # --------------------------------------------------------------------- UI
    def _reg(self, w, papel):
        self._tema_regs.append((w, papel))
        return w

    def _btn(self, pai, texto, comando, dica=None, largura=3):
        c = _cores()
        b = tk.Button(pai, text=texto, width=largura, command=comando, font=("Segoe UI", 9), relief="flat",
                      bg=c["neutro"], fg=c["texto"], activebackground=c["hover"], activeforeground=c["texto"])
        self._reg(b, "btn")
        if dica:
            ToolTip(b, dica)
        return b

    def _montar_ui(self):
        c = _cores()
        top = self.top = self._reg(tk.Frame(self, bg=c["fundo"]), "fundo")
        top.pack(fill="x", padx=6, pady=(6, 4))
        self._montar_barra_abas(top)
        self._montar_toolbar(top)
        self.slot_fav = self._reg(tk.Frame(top, bg=c["fundo"]), "fundo")
        self.slot_fav.pack(fill="x")
        self.barra_fav = self._reg(tk.Frame(self.slot_fav, bg=c["fundo"]), "fundo")
        self.barra_fav.bind("<Configure>", lambda e: self._agendar_layout_fav())
        self.slot_busca = self._reg(tk.Frame(top, bg=c["fundo"]), "fundo")
        self.slot_busca.pack(fill="x")
        self._aplicar_visibilidade_barra()

        self.container = tk.Frame(self, bg="white")
        self.container.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def _montar_barra_abas(self, top):
        c = _cores()
        self.barra_abas = self._reg(tk.Frame(top, bg=c["fundo"]), "fundo")
        self.barra_abas.pack(fill="x")
        self.btn_lista_abas = self._reg(tk.Label(self.barra_abas, text="⌄", font=("Segoe UI", 11), width=2,
                                                 bg=c["fundo"], fg=c["texto"], cursor="hand2"), "lbl")
        self.btn_lista_abas.pack(side="right")
        self.btn_lista_abas.bind("<Button-1>", lambda e: self._menu_lista_abas(e))
        ToolTip(self.btn_lista_abas, "Todas as abas")
        self.area_abas = self._reg(tk.Frame(self.barra_abas, bg=c["fundo"]), "fundo")
        self.area_abas.pack(side="left", fill="x", expand=True)
        self.area_abas.bind("<Configure>", lambda e: self._agendar_layout_abas())
        self.btn_nova_aba = self._reg(tk.Label(self.area_abas, text="＋", font=("Segoe UI", 12, "bold"), width=2,
                                               bg=c["fundo"], fg=c["texto"], cursor="hand2"), "lbl")
        self.btn_nova_aba.bind("<Button-1>", lambda e: self.nova_aba())
        ToolTip(self.btn_nova_aba, "Nova aba (Ctrl+T)")

    def _montar_toolbar(self, top):
        c = _cores()
        tb = self.toolbar = self._reg(tk.Frame(top, bg=c["fundo"]), "fundo")
        tb.pack(fill="x", pady=(4, 0))
        self.btn_voltar = self._btn(tb, "◀", self.voltar, "Voltar (Alt+←)")
        self.btn_voltar.pack(side="left", padx=1)
        self.btn_avancar = self._btn(tb, "▶", self.avancar, "Avançar (Alt+→)")
        self.btn_avancar.pack(side="left", padx=1)
        self.btn_recarregar = self._btn(tb, "⟳", self.recargar, "Recarregar (F5)")
        self.btn_recarregar.pack(side="left", padx=1)
        self.btn_home = self._btn(tb, "🏠", self.ir_home, "Página inicial (Alt+Home)")
        self.btn_home.pack(side="left", padx=1)

        self.btn_menu = self._btn(tb, "⋮", self.abrir_menu_principal, "Menu do navegador", largura=2)
        self.btn_menu.pack(side="right", padx=(4, 0))
        if self.on_capturar_url is not None:   # [Assistir] sem downloader: o botão não existe
            self.btn_capturar = tk.Button(
                tb, text="📥 Usar Vídeo no Painel", command=self.capturar_url, bg=ArduinoTheme.TEAL, fg="white",
                font=("Segoe UI", 9, "bold"), relief="flat", padx=10)
            self._reg(self.btn_capturar, "teal")
            self.btn_capturar.pack(side="right", padx=(4, 0))
        self.btn_ir = tk.Button(tb, text="Ir ➔", width=5, command=self.abrir_url, font=("Segoe UI", 9),
                                bg="#008184", fg="white", activebackground="#005c5e", activeforeground="white",
                                relief="flat")
        self._reg(self.btn_ir, "teal")
        self.btn_ir.pack(side="right", padx=(4, 0))
        self.btn_limpar_url = self._btn(tb, "✖", self._limpar_campo_url, None, largura=2)
        self.btn_limpar_url.pack(side="right", padx=(2, 2))

        self.caixa_url = self._reg(tk.Frame(tb, bg=c["borda"]), "caixa")
        self.caixa_url.pack(side="left", fill="x", expand=True, padx=(4, 2))
        interior = self._reg(tk.Frame(self.caixa_url, bg=c["campo"]), "campo")
        interior.pack(fill="both", expand=True, padx=1, pady=1)
        self.lbl_seguranca = self._reg(tk.Label(interior, text="🔍", font=("Segoe UI", 9), bg=c["campo"],
                                                fg=c["texto2"], width=3), "lbl_campo")
        self.lbl_seguranca.pack(side="left")
        self.btn_estrela = self._reg(tk.Label(interior, text="☆", font=("Segoe UI", 13), bg=c["campo"],
                                              fg=c["texto2"], cursor="hand2", width=2), "lbl_campo")
        self.btn_estrela.pack(side="right")
        self.btn_estrela.bind("<Button-1>", lambda e: self.favoritar_pagina())
        ToolTip(self.btn_estrela, "Favoritar esta página (Ctrl+D)")
        self.lbl_zoom = self._reg(tk.Label(interior, text="", font=("Segoe UI", 8), bg=c["campo"],
                                           fg=c["texto2"], cursor="hand2"), "lbl_campo")
        self.lbl_zoom.bind("<Button-1>", lambda e: self._mudar_zoom(0))
        ToolTip(self.lbl_zoom, "Zoom — clique para voltar a 100%")
        self.url_entry = self._reg(tk.Entry(interior, font=("Segoe UI", 10), relief="flat", bd=0, bg=c["campo"],
                                            fg=c["texto"], insertbackground=c["texto"]), "entry")
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=4)

    def reaplicar_tema(self):
        """Reaplica as cores do tema atual (claro/escuro) em todos os widgets do navegador."""
        c = _cores()
        regras = {
            "fundo": dict(bg=c["fundo"]),
            "campo": dict(bg=c["campo"]),
            "caixa": dict(bg=c["borda"]),
            "btn": dict(bg=c["neutro"], fg=c["texto"], activebackground=c["hover"], activeforeground=c["texto"]),
            "teal": dict(bg=ArduinoTheme.TEAL, fg="white"),
            "lbl": dict(bg=c["fundo"], fg=c["texto"]),
            "lbl_campo": dict(bg=c["campo"], fg=c["texto2"]),
            "entry": dict(bg=c["campo"], fg=c["texto"], insertbackground=c["texto"]),
        }
        for w, papel in list(self._tema_regs):
            try:
                w.configure(**regras[papel])
            except Exception:
                pass
        try:
            self._atualizar_chips()
            self._reconstruir_barra_favoritos()
            self._atualizar_estrela()
            self._atualizar_seguranca()
            self._atualizar_nav_botoes()
        except Exception:
            pass

    # ------------------------------------------------- eventos da barra de endereço
    def _montar_eventos_url(self):
        e = self.url_entry
        e.insert(0, "")
        e.bind("<Return>", self._ao_enter)
        e.bind("<KP_Enter>", self._ao_enter)
        e.bind("<Button-1>", self._ao_clicar_url)
        e.bind("<ButtonRelease-1>", self._ao_soltar_clique_url)
        e.bind("<FocusIn>", self._ao_focar_url)
        e.bind("<FocusOut>", self._ao_desfocar_url, add="+")
        e.bind("<FocusOut>", lambda ev: self.omni.ao_desfocar(), add="+")
        e.bind("<Key>", self._ao_digitar_url)
        e.bind("<Control-a>", self._selecionar_tudo)
        e.bind("<Control-A>", self._selecionar_tudo)
        e.bind("<KeyRelease>", self.omni.ao_soltar_tecla, add="+")
        e.bind("<Down>", lambda ev: self.omni.mover(1))
        e.bind("<Up>", lambda ev: self.omni.mover(-1))
        e.bind("<Escape>", self._ao_esc_url)
        e.bind("<Tab>", lambda ev: self.omni.aceitar_inline())
        e.bind("<Right>", self._ao_direita_url)
        e.bind("<Button-3>", self._menu_url)
        self.winfo_toplevel().bind("<Configure>", self._ao_mover_janela, add="+")

    def _ao_mover_janela(self, ev):
        if ev.widget is self.winfo_toplevel() and self.omni.aberto():
            self.omni.fechar()

    def _ao_enter(self, ev=None):
        linha = self.omni.confirmar()
        if linha:
            self.omni.escolher(linha)
        else:
            self.abrir_url()
        return "break"

    def _ao_esc_url(self, ev=None):
        if self.omni.aberto():
            restaurar = self.omni.sel >= 0
            self.omni.fechar()
            if restaurar:
                self._definir_entry(self.omni.digitado)
            return "break"
        aba = self.aba_ativa
        if aba is not None and self.url_entry.get() != aba.url:
            self.editando_url = False
            self._definir_entry(aba.url)
            return "break"
        return None

    def _ao_direita_url(self, ev=None):
        try:
            if self.url_entry.index(tk.INSERT) == len(self.url_entry.get()):
                return self.omni.aceitar_inline()
        except Exception:
            pass
        return None

    def _menu_url(self, ev):
        m = _menu_tema(self)
        e = self.url_entry
        m.add_command(label="Recortar", command=lambda: e.event_generate("<<Cut>>"))
        m.add_command(label="Copiar", command=lambda: e.event_generate("<<Copy>>"))
        m.add_command(label="Colar", command=lambda: e.event_generate("<<Paste>>"))
        m.add_command(label="Colar e ir", command=self._colar_e_ir)
        m.add_separator()
        m.add_command(label="Selecionar tudo", command=lambda: e.select_range(0, tk.END))
        m.tk_popup(ev.x_root, ev.y_root)
        return "break"

    def _colar_e_ir(self):
        try:
            texto = self.clipboard_get().strip()
        except tk.TclError:
            return
        if texto:
            self._definir_entry(texto)
            self.abrir_url()

    def _definir_entry(self, texto):
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, texto)

    def _forcar_foco_url(self):
        self.editando_url = True
        try:
            if os.name == "nt":
                import ctypes
                ctypes.windll.user32.SetFocus(self.url_entry.winfo_id())
        except Exception:
            pass
        self.url_entry.focus_force()

    def _ao_clicar_url(self, event=None):
        self._forcar_foco_url()

    def _ao_soltar_clique_url(self, event=None):
        self.editando_url = True

    def _ao_digitar_url(self, event=None):
        self.editando_url = True

    def _ao_focar_url(self, event=None):
        self._forcar_foco_url()
        self.after(60, lambda: self.url_entry.select_range(0, tk.END))

    def _ao_desfocar_url(self, event=None):
        texto = self.url_entry.get().strip()
        aba = self.aba_ativa
        if not texto or (aba is not None and texto == aba.url):
            self.editando_url = False

    def _selecionar_tudo(self, event=None):
        self.url_entry.select_range(0, tk.END)
        return "break"

    def _limpar_campo_url(self):
        self.editando_url = True
        self.url_entry.delete(0, tk.END)
        self._forcar_foco_url()
        self.omni.fechar()
        self._log("▶ [Comando] Campo de URL limpo")

    def focar_url(self):
        self._forcar_foco_url()
        self.url_entry.select_range(0, tk.END)
        self.url_entry.icursor(tk.END)

    # ------------------------------------------------------------------ atalhos
    def _montar_atalhos(self):
        raiz = self.winfo_toplevel()
        mapa = [
            ("<Control-t>", "nova_aba"), ("<Control-T>", "reabrir_aba"), ("<Control-w>", "fechar_aba"),
            ("<Control-l>", "foco_url"), ("<Control-L>", "foco_url"), ("<F6>", "foco_url"),
            ("<Control-d>", "favoritar"), ("<Control-D>", "favoritar"),
            ("<Control-f>", "localizar"), ("<Control-F>", "localizar"),
            ("<Control-h>", "historico"), ("<Control-H>", "historico"),
            ("<Control-j>", "downloads"), ("<Control-J>", "downloads"),
            ("<Control-B>", "barra_favoritos"), ("<Control-O>", "favoritos"), ("<Control-N>", "nova_anonima"),
            ("<Control-plus>", "zoom_mais"), ("<Control-equal>", "zoom_mais"),
            ("<Control-minus>", "zoom_menos"), ("<Control-0>", "zoom_zero"),
            ("<Control-Tab>", "aba_prox"), ("<Control-ISO_Left_Tab>", "aba_ant"),
            ("<Control-Next>", "aba_prox"), ("<Control-Prior>", "aba_ant"),
            ("<Alt-Home>", "home"), ("<F5>", "recarregar"), ("<Control-r>", "recarregar"),
            ("<Alt-Left>", "voltar"), ("<Alt-Right>", "avancar"),
        ] + [(f"<Control-Key-{i}>", f"aba_{i}") for i in range(1, 10)]
        for seq, cmd in mapa:
            acao = (lambda e, c=cmd: (self.executar_comando(c, origem="tk"), "break")[1])
            raiz.bind(seq, acao, add="+")
            # o Entry tem atalhos próprios (Ctrl+D apaga letra, Ctrl+T troca letras...): vence o nosso
            self.url_entry.bind(seq, acao)

    def executar_comando(self, nome, origem="js"):
        agora = time.time()
        if agora - self._ult_cmd.get(nome, 0.0) < 0.15:
            return
        self._ult_cmd[nome] = agora
        m = re.match(r"^aba_([1-9])$", nome)
        if m:
            self.ir_para_aba_n(int(m.group(1)))
            return
        acoes = {
            "nova_aba": lambda: self.nova_aba(), "nova_anonima": lambda: self.nova_aba(anonima=True),
            "fechar_aba": lambda: self.fechar_aba(), "reabrir_aba": self.reabrir_aba,
            "foco_url": self.focar_url, "favoritar": self.favoritar_pagina, "localizar": self.abrir_busca,
            "historico": self.abrir_historico, "downloads": self.abrir_downloads,
            "barra_favoritos": self.alternar_barra_favoritos, "favoritos": self.abrir_gerenciador_favoritos,
            "aba_prox": lambda: self.aba_relativa(1), "aba_ant": lambda: self.aba_relativa(-1),
            "zoom_mais": lambda: self._mudar_zoom(1), "zoom_menos": lambda: self._mudar_zoom(-1),
            "zoom_zero": lambda: self._mudar_zoom(0), "home": self.ir_home,
            "recarregar": self.recargar, "voltar": self.voltar, "avancar": self.avancar,
            "aviso_close": lambda: self._log("🛡 O site tentou fechar a janela (window.close). Ignorado."),
        }
        fn = acoes.get(nome)
        if fn:
            try:
                fn()
            except Exception as e:
                self._log(f"⚠ Atalho '{nome}' falhou: {e}")

    # -------------------------------------------------------------------- abas
    def _iniciar(self):
        urls, ativa = [], 0
        if self.cfg.get("ao_iniciar") == "continuar":
            s = self.cfg.get("sessao") or {}
            urls = [u for u in (s.get("urls") or []) if _url_navegavel(u)][:20]
            ativa = s.get("ativa", 0) if isinstance(s.get("ativa", 0), int) else 0
        if not urls:
            urls = [self.cfg.get("home")]
        for u in urls:
            self._nova_aba_obj(u)
        self.ativar_aba(self.abas[min(max(ativa, 0), len(self.abas) - 1)])
        self.after(1000, self._verificar_url_periodica)
        self.after(5000, self._batimento)

    def _nova_aba_obj(self, url, anonima=False, indice=None):
        aba = _Aba(url, anonima)
        aba.frame = tk.Frame(self.container, bg="white")
        aba.lbl_espera = tk.Label(aba.frame, text="Iniciando Navegador...", font=("Segoe UI", 11),
                                  bg="white", fg="#666")
        aba.lbl_espera.pack(expand=True)
        if indice is None:
            self.abas.append(aba)
        else:
            self.abas.insert(indice, aba)
        self._criar_chip(aba)
        self._atualizar_chips()
        return aba

    def nova_aba(self, url=None, ativar=True, anonima=False, ao_lado=False):
        if len(self.abas) >= self.MAX_ABAS:
            self._log(f"⚠ Limite de {self.MAX_ABAS} abas atingido")
            return None
        if url is not None and not _url_navegavel(url):
            url = None
        indice = None
        if ao_lado and self.aba_ativa in self.abas:
            indice = self.abas.index(self.aba_ativa) + 1
        aba = self._nova_aba_obj(url, anonima, indice)
        if ativar:
            self.ativar_aba(aba)
            if url is None:
                self.after(150, self.focar_url)
        if anonima:
            self._log("🕶 Aba anônima aberta: nada é salvo no histórico")
        return aba

    def ativar_aba(self, aba):
        if aba is None or aba.fechada or aba not in self.abas:
            return
        anterior = self.aba_ativa
        if anterior is not None and anterior is not aba:
            try:
                anterior.frame.pack_forget()
            except Exception:
                pass
            self._fechar_busca()
        self.aba_ativa = aba
        aba.ultimo_ok, aba.bat_pend = time.time(), 0.0
        aba.frame.pack(fill="both", expand=True)
        self.omni.fechar()
        self.editando_url = False
        if aba.webview is None and not aba.criando:
            self.after(60, lambda a=aba: self._criar_webview(a))
        else:
            self.after(40, self._sync_bounds)
        self._sincronizar_barra()
        self._aplicar_zoom(aba)
        if self.on_url_mudou and _url_navegavel(aba.url) and anterior is not aba:
            try:
                self.on_url_mudou(aba.url)
            except Exception:
                pass

    def _sync_bounds(self):
        try:
            wv = self.webview
            if wv is not None:
                wv.sync_bounds()
        except Exception:
            pass

    def fechar_aba(self, aba=None):
        aba = aba or self.aba_ativa
        if aba is None or aba not in self.abas:
            return
        if len(self.abas) == 1:
            nova = self._nova_aba_obj(None)
            self._destruir_aba(aba, lembrar=True)
            self.ativar_aba(nova)
            self.after(150, self.focar_url)
            return
        idx = self.abas.index(aba)
        era_ativa = aba is self.aba_ativa
        self._destruir_aba(aba, lembrar=True)
        if era_ativa:
            self.ativar_aba(self.abas[min(idx, len(self.abas) - 1)])
        else:
            self._atualizar_chips()

    def _destruir_aba(self, aba, lembrar):
        aba.fechada = True
        if lembrar and not aba.anonima and _url_navegavel(aba.url):
            self._fechadas.append((aba.url, aba.titulo))
            del self._fechadas[:-20]
        if aba.hist_after:
            try:
                self.after_cancel(aba.hist_after)
            except Exception:
                pass
        if aba in self.abas:
            self.abas.remove(aba)
        if aba.chip:
            try:
                aba.chip["f"].destroy()
            except Exception:
                pass
        if aba.webview is not None:
            try:
                aba.webview.destroy()
            except Exception:
                pass
            aba.webview = None
        try:
            aba.frame.destroy()
        except Exception:
            pass
        if aba is self.aba_ativa:
            self.aba_ativa = None
        if aba.anonima and not any(a.anonima for a in self.abas) and self._sessao_anonima is not None:
            try:
                self._sessao_anonima.close()
            except Exception:
                pass
            self._sessao_anonima = None

    def reabrir_aba(self):
        if not self._fechadas:
            self._log("ℹ Nenhuma aba fechada para reabrir")
            return
        url, _t = self._fechadas.pop()
        self.nova_aba(url)

    def duplicar_aba(self, aba):
        if aba and _url_navegavel(aba.url) and len(self.abas) < self.MAX_ABAS:
            self._nova_aba_ao_lado(aba)

    def _nova_aba_ao_lado(self, aba):
        nova = self._nova_aba_obj(aba.url, aba.anonima, self.abas.index(aba) + 1)
        self.ativar_aba(nova)

    def fechar_outras(self, aba):
        for a in [x for x in self.abas if x is not aba]:
            self._destruir_aba(a, lembrar=True)
        self.ativar_aba(aba)

    def fechar_direita(self, aba):
        if aba not in self.abas:
            return
        for a in self.abas[self.abas.index(aba) + 1:]:
            self._destruir_aba(a, lembrar=True)
        self._atualizar_chips()

    def aba_relativa(self, delta):
        if len(self.abas) < 2 or self.aba_ativa not in self.abas:
            return
        i = (self.abas.index(self.aba_ativa) + delta) % len(self.abas)
        self.ativar_aba(self.abas[i])

    def ir_para_aba_n(self, n):
        if not self.abas:
            return
        self.ativar_aba(self.abas[-1] if n == 9 else self.abas[n - 1] if n - 1 < len(self.abas) else None)

    # --- chips (as "orelhas" das abas)
    def _criar_chip(self, aba):
        f = tk.Frame(self.area_abas, height=30)
        f.pack_propagate(False)
        acento = tk.Frame(f, height=2)
        acento.pack(side="top", fill="x")
        lbl = tk.Label(f, anchor="w", font=("Segoe UI", 9), cursor="hand2")
        lbl.pack(side="left", fill="both", expand=True, padx=(8, 0))
        x = tk.Label(f, text="✕", font=("Segoe UI", 8), width=2, cursor="hand2")
        x.pack(side="right", padx=(0, 4))
        for w in (f, acento, lbl):
            w.bind("<Button-1>", lambda e, a=aba: self.ativar_aba(a))
            w.bind("<Button-2>", lambda e, a=aba: self.fechar_aba(a))
            w.bind("<Button-3>", lambda e, a=aba: self._menu_aba(e, a))
        x.bind("<Button-1>", lambda e, a=aba: (self.fechar_aba(a), "break")[1])
        x.bind("<Enter>", lambda e, w=x: w.configure(fg=_cores()["perigo"]))
        x.bind("<Leave>", lambda e, a=aba: self._atualizar_chips())
        aba.chip = {"f": f, "acento": acento, "lbl": lbl, "x": x}

    _SPIN = "◐◓◑◒"

    def _texto_chip(self, aba, larg):
        pre = (self._SPIN[self._spin_i % 4] + " ") if aba.carregando else ""
        if aba.anonima:
            pre += "🕶 "
        base = aba.titulo or (_host_de(aba.url).replace("www.", "") if aba.url else
                              ("Nova aba" if aba.inicio else "Carregando…"))
        txt = pre + base
        maxc = max(3, (larg - 44) // 7)
        return txt if len(txt) <= maxc else txt[:maxc - 1] + "…"

    def _agendar_layout_abas(self):
        if self._layout_abas_after:
            try:
                self.after_cancel(self._layout_abas_after)
            except Exception:
                pass
        self._layout_abas_after = self.after(80, self._atualizar_chips)

    def _atualizar_chips(self):
        self._layout_abas_after = None
        try:
            c = _cores()
            n = max(1, len(self.abas))
            disp = self.area_abas.winfo_width()
            if disp < 120:
                disp = 700
            larg = max(64, min(210, (disp - 44) // n))
            for aba in self.abas:
                aba.chip["f"].pack_forget()
            for aba in self.abas:
                ch, ativa = aba.chip, aba is self.aba_ativa
                bg = c["campo"] if ativa else c["neutro"]
                fg = c["texto"] if ativa else c["texto2"]
                ch["f"].configure(width=larg, height=30, bg=bg)
                ch["acento"].configure(bg=c["teal"] if ativa else bg)
                ch["lbl"].configure(bg=bg, fg=fg, text=self._texto_chip(aba, larg))
                ch["x"].configure(bg=bg, fg=fg)
                ch["f"].pack(side="left", padx=(0, 2))
            self.btn_nova_aba.pack_forget()
            self.btn_nova_aba.pack(side="left", padx=(4, 0))
            self.btn_nova_aba.configure(bg=c["fundo"], fg=c["texto"])
            self.btn_lista_abas.configure(bg=c["fundo"], fg=c["texto"])
        except tk.TclError:
            pass

    def _atualizar_chip_texto(self, aba):
        try:
            larg = int(aba.chip["f"].cget("width"))
            aba.chip["lbl"].configure(text=self._texto_chip(aba, larg))
        except Exception:
            pass

    def _set_carregando(self, aba, v):
        if aba.carregando == v:
            return
        aba.carregando = v
        aba.carga_t = time.time() if v else 0.0
        if v and self._spin_after is None:
            self._spin_after = self.after(150, self._girar)
        self._atualizar_chip_texto(aba)
        if aba is self.aba_ativa:
            self._atualizar_botao_recarregar()

    def _girar(self):
        self._spin_after = None
        mudou = False
        algum = False
        for a in list(self.abas):
            if a.carregando:
                if time.time() - a.carga_t > 45:
                    a.carregando = False
                    mudou = True
                else:
                    algum = True
                    self._atualizar_chip_texto(a)
        self._spin_i += 1
        if algum:
            self._spin_after = self.after(150, self._girar)
        if mudou:
            self._atualizar_chips()
            self._atualizar_botao_recarregar()

    def _menu_aba(self, ev, aba):
        m = _menu_tema(self)
        m.add_command(label="Nova aba", command=self.nova_aba)
        m.add_command(label="Recarregar", command=lambda: self._recarregar_aba(aba))
        m.add_command(label="Duplicar", command=lambda: self.duplicar_aba(aba))
        m.add_separator()
        m.add_command(label="Fechar", command=lambda: self.fechar_aba(aba))
        m.add_command(label="Fechar outras abas", command=lambda: self.fechar_outras(aba))
        m.add_command(label="Fechar abas à direita", command=lambda: self.fechar_direita(aba))
        m.add_separator()
        m.add_command(label="Reabrir aba fechada", command=self.reabrir_aba,
                      state="normal" if self._fechadas else "disabled")
        m.tk_popup(ev.x_root, ev.y_root)
        return "break"

    def _menu_lista_abas(self, ev):
        m = _menu_tema(self)
        for i, a in enumerate(self.abas):
            nome = (a.titulo or a.url or "Nova aba")
            nome = ("🕶 " if a.anonima else "") + (nome if len(nome) <= 60 else nome[:59] + "…")
            m.add_command(label=("● " if a is self.aba_ativa else "   ") + nome, command=lambda x=a: self.ativar_aba(x))
        m.tk_popup(ev.x_root, ev.y_root)

    def abas_visiveis(self):
        return list(self.abas)

    # ------------------------------------------------------------- WebView/aba
    def _obter_sessao(self, anonima):
        from tkwry import WebSession
        if anonima:
            if self._sessao_anonima is None or self._sessao_anonima.closed:
                self._sessao_anonima = WebSession(ephemeral=True)
            return self._sessao_anonima
        if self._sessao_normal is None:
            caminho = os.path.join(os.path.expanduser("~"), ".youdown", "browser_data")
            os.makedirs(caminho, exist_ok=True)
            self._sessao_normal = WebSession(data_directory=caminho)
        return self._sessao_normal

    def _html_nova_aba(self):
        c = _cores()
        h = c["campo"].lstrip("#")
        try:
            lum = sum(int(h[i:i + 2], 16) for i in (0, 2, 4)) / 3
        except Exception:
            lum = 255
        escuro = lum < 110
        bg, fg = ("#202124", "#e8eaed") if escuro else ("#ffffff", "#2d2d2d")
        card, sub = ("#2d2e31", "#9aa0a6") if escuro else ("#f4f4f4", "#5c5c5c")
        vistos, tiles = set(), []
        fontes = [(n["url"], n["titulo"]) for n in self.favoritos.raizes["barra"] if n["tipo"] == "link"]
        fontes += self.historico.mais_visitados(10)
        for url, tit in fontes:
            ch = _chave_url(url)
            if ch in vistos or not _url_navegavel(url) or len(tiles) >= 10:
                continue
            vistos.add(ch)
            nome = (tit or _host_de(url)).strip() or url
            nome = nome if len(nome) <= 22 else nome[:21] + "…"
            letra = _html.escape((nome[:1] or "?").upper())
            tiles.append(f'<a class="t" href="{_html.escape(url, quote=True)}"><div class="i">{letra}</div>'
                         f'<span>{_html.escape(nome)}</span></a>')
        motor = self.cfg.get("busca")
        nome_motor = _MOTORES_BUSCA[motor][0]
        modelo = json.dumps(_MOTORES_BUSCA[motor][1])
        return rf"""<!doctype html><html><head><meta charset="utf-8"><title>Nova aba</title>
<style>
html,body{{margin:0;height:100%;background:{bg};color:{fg};font-family:'Segoe UI',Arial,sans-serif}}
.w{{display:flex;flex-direction:column;align-items:center;padding-top:12vh}}
h1{{font-weight:300;font-size:30px;margin:0 0 22px}}
input{{width:min(560px,86vw);padding:13px 20px;border-radius:26px;border:1px solid {sub}55;font-size:16px;
background:{card};color:{fg};outline:none}}
input:focus{{border-color:#008184;box-shadow:0 0 0 2px #00818455}}
.g{{display:grid;grid-template-columns:repeat(5,110px);gap:14px;margin-top:34px;justify-content:center}}
.t{{display:flex;flex-direction:column;align-items:center;gap:8px;padding:14px 6px;border-radius:10px;
text-decoration:none;color:{fg};font-size:12px;text-align:center}}
.t:hover{{background:{card}}}
.i{{width:44px;height:44px;border-radius:50%;background:#008184;color:#fff;display:flex;align-items:center;
justify-content:center;font-size:20px;font-weight:600}}
@media(max-width:700px){{.g{{grid-template-columns:repeat(3,110px)}}}}
</style></head><body><div class="w"><h1>Nova aba</h1>
<form id="f"><input name="q" autofocus autocomplete="off" placeholder="Pesquisar no {_html.escape(nome_motor)} ou digitar um endereço"></form>
<div class="g">{''.join(tiles)}</div></div>
<script>
var M = {modelo};
document.getElementById('f').addEventListener('submit', function(e) {{
  e.preventDefault();
  var q = this.q.value.trim(); if (!q) return;
  var u;
  if (/^https?:\/\//i.test(q)) u = q;
  else if (/^[\w-]+(\.[\w-]+)+(\/\S*)?$/.test(q)) u = 'https://' + q;
  else u = M.replace('{{}}', encodeURIComponent(q));
  location.href = u;
}});
</script></body></html>"""

    def _criar_webview(self, aba):
        if aba.webview is not None or aba.criando or aba.fechada:
            return
        aba.criando = True
        try:
            from tkwry import WebView, NewWindowResponse, PageLoadEvent
            self._PLE = PageLoadEvent
            try:
                aba.lbl_espera.destroy()
            except Exception:
                pass

            def _popup(event):
                self._decidir_popup(aba, getattr(event, "url", "") or "")
                return NewWindowResponse.Deny

            kw = dict(
                session=self._obter_sessao(aba.anonima), javascript_enabled=True, autoplay=True,
                devtools=True, initialization_script=INIT_JS,
                on_new_window=_popup,
                on_navigation=lambda ev, a=aba: self._ao_navegar(a, ev),
                on_title_changed=lambda t, a=aba: self._ao_titulo(a, t),
                on_page_load=lambda ev, u, a=aba: self._ao_carregar(a, ev, u),
                on_download=lambda dl, a=aba: self._ao_baixar(a, dl),
                on_download_complete=lambda dl, ok, a=aba: self._ao_baixou(a, dl, ok),
            )
            if aba.inicio:
                kw["html"] = self._html_nova_aba()
            else:
                kw["url"] = aba.url_inicial or aba.url
                self._liberar_navegacao(aba, kw["url"], seg=20.0)
            wv = WebView(aba.frame, **kw)
            aba.webview = wv
            wv.pack(fill="both", expand=True)
            if not self._aviso_ativo_logado:
                self._aviso_ativo_logado = True
                self._log("Navegador ativo (AdBlock Universal + Anti-Popup + Modo Estrito Redecanais).")
        except Exception as e:
            msg_erro = str(e)
            dica = ""
            if "tkwry" in msg_erro:
                dica = ("\n\n💡 Para rodar via script .py, instale as dependências no terminal:\npip install tkwry yt-dlp"
                        "\n\n(Ou execute o Assistir.exe, que já vem com tudo embutido!)")
            try:
                aba.lbl_espera.config(text=f"Erro ao carregar WebView: {e}{dica}")
            except Exception:
                pass
            self._log(f"❌ [Falha] Falha ao iniciar WebView2: {e}")
            if "tkwry" in msg_erro:
                self._log("💡 Dica: instale a dependência com: pip install tkwry yt-dlp")
                self._log("💡 Ou utilize o executável Assistir.exe (já vem com tudo embutido).")
        finally:
            aba.criando = False

    # --- barreira de navegação (modo estrito) e popups: por aba
    @staticmethod
    def _norm_url(u):
        return str(u or "").strip().rstrip("/").lower()

    def _liberar_navegacao(self, aba, url=None, seg=3.0):
        """Autoriza UMA navegação pedida pelo usuário (url=None: qualquer uma)."""
        aba.nav_livre = {"url": self._norm_url(url) if url else None, "ate": time.time() + seg}

    def _avisar_bloqueio(self, aba, msg, url):
        chave = _host_de(url) + msg
        agora = time.time()
        if chave == aba.ult_aviso[0] and agora - aba.ult_aviso[1] < 3:
            return
        aba.ult_aviso = (chave, agora)
        self._log_seguro(f"{msg}: {str(url)[:70]}")

    def _ao_navegar(self, aba, event):
        """Chamado antes de QUALQUER navegação da página principal da aba.
        Retorna True para permitir e False para bloquear (precisa ser bool)."""
        try:
            destino = getattr(event, "url", "") or ""
            self._escrever_log(f"navegação: {destino[:150]}")
            if not destino.startswith(("http://", "https://")):
                return True
            livre = aba.nav_livre
            if livre and time.time() < livre["ate"]:
                if livre["url"] is None or livre["url"] == self._norm_url(destino):
                    aba.nav_livre = None
                    aba.ref_nav = destino
                    return True
            ref = aba.ref_nav or aba.url
            if _url_de_anuncio(destino):
                self._avisar_bloqueio(aba, "🛡 Redirecionamento de anúncio bloqueado", destino)
                return False
            if _eh_site_estrito(ref) and not _mesmo_site(destino, ref):
                self._avisar_bloqueio(
                    aba, "🛡 Saída do site bloqueada (modo estrito). Para ir a outro endereço, digite-o na barra",
                    destino)
                return False
            aba.ref_nav = destino
            return True
        except Exception:
            return True

    def _decidir_popup(self, aba, u):
        """Nunca abre janela nativa: bloqueia anúncios e abre links legítimos em NOVA ABA."""
        self._escrever_log(f"popup solicitado: {u[:150]}")
        if not u or u == "about:blank":
            return
        u_lower = u.lower()
        ref = aba.ref_nav or aba.url
        abrir = False
        if _eh_site_estrito(ref):
            if (u.startswith(("http://", "https://")) and _mesmo_site(u, ref)
                    and not _url_de_anuncio(u) and not _RE_URL_SUSPEITA.search(u)):
                abrir = True
            else:
                self._avisar_bloqueio(aba, "🛡 Popup bloqueado (modo estrito)", u)
        else:
            ad_patterns = ["bet", "cassino", "casino", "blaze", "popads", "popcash", "propeller", "adsterra",
                           "exoclick", "track", "affiliat", "doubleclick", "traffic", "histats"]
            if any(p in u_lower for p in ad_patterns) or _url_de_anuncio(u):
                self._log_seguro(f"🛡 Popup de anúncio bloqueado: {u[:60]}")
            elif u.startswith(("http://", "https://")):
                abrir = True
        if abrir and _eh_site_estrito(ref):
            self._log_seguro(f"🔗 Navegando: {u[:60]}")
            self._fila_ui.put(("navegar", u, aba))
        elif abrir:
            self._log_seguro(f"🔗 Abrindo em nova aba: {u[:60]}")
            self._fila_ui.put(("nova_aba", u, aba.anonima))

    # --- eventos do WebView
    def _ao_titulo(self, aba, titulo):
        if aba.fechada:
            return
        titulo = (titulo or "").strip()
        if not titulo or titulo.lower() == "about:blank":
            return
        aba.titulo = titulo
        self._atualizar_chip_texto(aba)
        if not aba.anonima and aba.url:
            self.historico.atualizar_titulo(aba.url, titulo)
            self._agendar_salvar()
        if aba is self.aba_ativa:
            self._atualizar_estrela()

    def _ao_carregar(self, aba, evento, url):
        if aba.fechada:
            return
        nome = str(getattr(evento, "name", evento)).lower()
        self._escrever_log(f"página {'iniciou' if 'start' in nome else 'terminou'}: {str(url)[:120]}")
        if "start" in nome:
            self._set_carregando(aba, True)
            return
        self._set_carregando(aba, False)
        u = _limpar_marcas(url or "")
        if _url_navegavel(u):
            self._ao_mudar_url(aba, u)
        aba.carga_ok_t = time.time()
        aba.ultimo_ok = time.time()
        aba.zoom_aplicado = None
        self._aplicar_zoom(aba)
        self._agendar_historico(aba)
        if aba is self.aba_ativa:
            self._atualizar_nav_botoes()

    def _ao_mudar_url(self, aba, url):
        url = _limpar_marcas(url)
        if aba.fechada or not url or url == aba.url:
            return
        if _url_navegavel(aba.url):
            aba.url_anterior = aba.url
        aba.url = url
        aba.ref_nav = url
        aba.inicio = False
        if aba is self.aba_ativa:
            try:
                texto = self.url_entry.get().strip()
                if not self.editando_url and (not texto or texto == url or self.focus_get() is not self.url_entry):
                    self._definir_entry(url)
            except Exception:
                pass
            self._sincronizar_barra()
            self._aplicar_zoom(aba)
            self._log(f"🌐 Página navegada: {url}")
            if self.on_url_mudou:
                self.on_url_mudou(url)
        else:
            self._atualizar_chip_texto(aba)
        self._agendar_historico(aba)

    # --- downloads
    def _ao_baixar(self, aba, dl):
        if self.bloquear_downloads:   # [Assistir] "só assistir": cancela qualquer download
            self._log_seguro(f"🛡 Download bloqueado (só assistir): {str(getattr(dl, 'url', ''))[:60]}")
            return False
        try:
            pasta = os.path.join(os.path.expanduser("~"), "Downloads")
            destino = dl.save(pasta)
            self._dl_id += 1
            self.downloads.append({"id": self._dl_id, "nome": os.path.basename(destino), "url": dl.url,
                                   "destino": destino, "estado": "baixando", "t": time.time()})
            self._log_seguro(f"📥 Download iniciado: {os.path.basename(destino)}  (Ctrl+J para acompanhar)")
            return destino
        except Exception as e:
            self._log_seguro(f"❌ Download não iniciado: {e}")
            return None

    def _ao_baixou(self, aba, dl, ok):
        destino = getattr(dl, "dest", None) or getattr(dl, "suggested_dest", "")
        alvo = None
        for d in reversed(self.downloads):
            if d["estado"] == "baixando" and (d["destino"] == destino or d["url"] == dl.url):
                alvo = d
                break
        if alvo is None:
            for d in reversed(self.downloads):
                if d["estado"] == "baixando":
                    alvo = d
                    break
        if alvo is not None:
            alvo["estado"] = "concluido" if ok else "falhou"
        nome = os.path.basename(destino or "") or "arquivo"
        self._log(f"✔ Download concluído: {nome}" if ok else f"✖ Download falhou: {nome}")

    # ------------------------------------------------------------- navegação
    def _wv(self, aba=None):
        aba = aba or self.aba_ativa
        wv = aba.webview if aba else None
        return wv if (wv is not None and wv.ready) else None

    def navegar_para(self, url, aba=None):
        aba = aba or self.aba_ativa
        if aba is None or not url:
            return
        aba.url = url
        aba.inicio = False
        aba.titulo = ""
        wv = self._wv(aba)
        if wv is None:
            aba.url_inicial = url
            if aba is self.aba_ativa:
                self._definir_entry(url)
                self._sincronizar_barra()
            if aba.webview is None and aba is self.aba_ativa and not aba.criando:
                self.after(60, lambda a=aba: self._criar_webview(a))
            return
        try:
            self._liberar_navegacao(aba, url)
            wv.load_url(url)
        except Exception as e:
            self._log(f"❌ Erro ao navegar: {e}")
            return
        if aba is self.aba_ativa:
            self.editando_url = False
            self._definir_entry(url)
            self._sincronizar_barra()

    def abrir_url_direta(self, url):
        self.navegar_para(url)

    def _abrir_sugestao(self, linha):
        tipo = linha["tipo"]
        if tipo == "aba" and linha.get("aba") is not None:
            self.ativar_aba(linha["aba"])
            return
        if tipo == "online":
            url = _url_de_busca(self.cfg.get("busca"), linha["titulo"])
        else:
            url = linha["url"]
        if tipo == "acao" and _url_navegavel(url) and linha.get("titulo") == url and self.on_site_digitado:   # [Assistir]
            try:
                self.on_site_digitado(url)
            except Exception as e:
                self._escrever_log(f"erro em on_site_digitado: {e}")
        self._log(f"▶ [Comando] Navegar para URL: {url}")
        self.navegar_para(url)
        try:
            self.url_entry.selection_clear()
        except Exception:
            pass

    def abrir_url(self):
        self.editando_url = False
        self.omni.fechar()
        texto = self.url_entry.get().strip()
        if not texto:
            self._log("⚠ [Aviso] Nenhuma URL digitada na barra de endereços")
            return
        _tipo, url = _interpretar_entrada(texto, self.cfg.get("busca"))
        if not url:
            return
        self._log(f"▶ [Comando] Navegar para URL: {url}")
        if self.aba_ativa is None or (self._wv() is None and self.aba_ativa.webview is not None):
            self._log(f"❌ [Falha] Navegador indisponível para carregar URL: {url}")
            return
        if _tipo == "url" and self.on_site_digitado:   # [Assistir]
            try:
                self.on_site_digitado(url)
            except Exception as e:
                self._escrever_log(f"erro em on_site_digitado: {e}")
        self.navegar_para(url)

    def ir_home(self):
        self._log("▶ [Comando] Navegador: Ir para página inicial")
        self.navegar_para(self.cfg.get("home"))

    def voltar(self):
        self._log("▶ [Comando] Navegador: Voltar página")
        self._navegar_historico("go_back", "voltar")

    def avancar(self):
        self._log("▶ [Comando] Navegador: Avançar página")
        self._navegar_historico("go_forward", "avançar")

    def _navegar_historico(self, metodo, rotulo):
        aba, wv = self.aba_ativa, self._wv()
        if wv is None:
            self._log(f"❌ [Falha] Navegador indisponível para {rotulo}")
            return
        try:
            self._liberar_navegacao(aba, None, seg=1.5)
            getattr(wv, metodo)()
        except Exception as e:
            self._log(f"❌ [Falha] Falha ao {rotulo} página: {e}")

    def _recarregar_aba(self, aba):
        wv = self._wv(aba)
        if wv is None:
            return
        try:
            self._liberar_navegacao(aba, None, seg=1.5)
            wv.reload()
        except Exception as e:
            self._log(f"❌ [Falha] Falha ao recarregar página: {e}")

    def recargar(self):
        aba = self.aba_ativa
        if aba is not None and aba.carregando:
            self.parar()
            return
        self._log("▶ [Comando] Navegador: Recarregar página")
        if aba is None or self._wv() is None:
            self._log("❌ [Falha] Navegador indisponível para recarregar")
            return
        self._recarregar_aba(aba)

    def parar(self):
        wv = self._wv()
        if wv is not None:
            try:
                wv.eval_js("window.stop()")
            except Exception:
                pass
        if self.aba_ativa is not None:
            self._set_carregando(self.aba_ativa, False)

    def capturar_url(self):
        self._log("▶ [Comando] Capturar URL do navegador para download")
        url = None
        wv = self._wv()
        if wv is not None:
            try:
                url = _limpar_marcas(wv.url)
            except Exception as e:
                self._log(f"⚠ [Aviso] Falha ao obter URL atual do navegador: {e}")
        if not url:
            url = self.url_entry.get().strip()
        if url:
            if self.on_capturar_url:
                self.on_capturar_url(url)
            self._log(f"✓ URL enviada para o painel de download: {url}")
        else:
            self._log("❌ [Falha] Nenhuma URL válida encontrada para capturar")

    def alternar_fullscreen(self):
        if self.on_fullscreen:
            self.on_fullscreen()

    def abrir_navegador_youtube(self):
        pass

    # ------------------------------------------- acompanhamento da aba ativa
    def _verificar_url_periodica(self):
        try:
            aba = self.aba_ativa
            wv = aba.webview if aba else None
            if wv is not None and wv.ready:
                url = wv.url
                if url:
                    agora = time.time()
                    if agora >= getattr(self, "_ignorar_fs_ate", 0):
                        # Detecta eventos de tela cheia do site via sequência atômica (in/out)
                        m = re.search(r'__youdown_fs_(in|out)__=(\d+)', url)
                        if m:
                            tipo, seq = m.group(1), int(m.group(2))
                            if seq != getattr(self, "_fs_ultimo_seq", 0):
                                self._fs_ultimo_seq = seq
                                if tipo == "in":
                                    if not self.navegador_em_fs and self.on_fullscreen:
                                        self._fs_disparado_por_site = True
                                        self.on_fullscreen(True)
                                elif tipo == "out":
                                    if self.navegador_em_fs and self.on_fullscreen:
                                        self._fs_disparado_por_site = False
                                        self.on_fullscreen(False)
                    mc = _RE_MARCA_CMD.search(url)
                    if mc and int(mc.group(2)) != aba.cmd_seq:
                        aba.cmd_seq = int(mc.group(2))
                        nome = mc.group(1)
                        try:
                            wv.eval_js(_JS_LIMPAR_CMD)
                        except Exception:
                            pass
                        if nome in _COMANDOS_JS_OK:
                            self.executar_comando(nome, origem="js")
                    url_limpa = _limpar_marcas(url)
                    if _url_navegavel(url_limpa) and url_limpa != aba.url:
                        self._ao_mudar_url(aba, url_limpa)
                        try:
                            wv.eval_js(INIT_JS)
                        except Exception:
                            pass
        except Exception:
            pass
        finally:
            self.after(100, self._verificar_url_periodica)

    # ------------------------------------- a página ainda está viva? (autorrecuperação)
    def _batimento(self):
        """A cada 5 s pergunta '1' à página. Se ela não responde por 20 s (processo morreu ou travou
        de vez, ex.: window.close() destruindo a página), a aba é recriada."""
        try:
            aba = self.aba_ativa
            wv = self._wv(aba) if aba is not None else None
            if wv is not None and not aba.fechada:
                agora = time.time()
                if aba.carregando or aba.ultimo_ok == 0.0:
                    aba.ultimo_ok, aba.bat_pend = agora, 0.0
                if aba.bat_pend == 0.0:
                    aba.bat_pend = agora

                    def resposta(_r, a=aba):
                        a.ultimo_ok, a.bat_pend = time.time(), 0.0
                    try:
                        wv.eval_js_with_callback("1", resposta, on_error=lambda e: None)
                    except Exception:
                        aba.bat_pend = 0.0
                if agora - aba.ultimo_ok > 20:
                    self._recuperar_aba(aba, "sem resposta há 20 s")
        except Exception:
            pass
        finally:
            self.after(5000, self._batimento)

    def _recuperar_aba(self, aba, motivo):
        if aba.fechada:
            return
        agora = time.time()
        aba.recuperacoes = [t for t in aba.recuperacoes if agora - t < 60] + [agora]
        url = aba.url or aba.url_inicial or ""
        if agora - aba.carga_ok_t < 10 and _url_navegavel(aba.url_anterior):
            url = aba.url_anterior          # travou logo ao abrir: volta p/ a página anterior (evita loop)
        self._log(f"⚠ A página parou de responder ({motivo}). Recriando a aba…")
        if aba.webview is not None:
            try:
                aba.webview.destroy()
            except Exception:
                pass
        aba.webview = None
        aba.criando = False
        aba.carregando = False
        try:
            aba.frame.destroy()
        except Exception:
            pass
        aba.frame = tk.Frame(self.container, bg="white")
        aba.lbl_espera = tk.Label(aba.frame, text="Reabrindo a página…", font=("Segoe UI", 11), bg="white", fg="#666")
        aba.lbl_espera.pack(expand=True)
        aba.ultimo_ok, aba.bat_pend = agora, 0.0
        if aba is self.aba_ativa:
            aba.frame.pack(fill="both", expand=True)
        if _url_navegavel(url):
            aba.url = aba.url_inicial = url
            aba.inicio = False
        else:
            aba.url, aba.url_inicial, aba.inicio = "", None, True
        if len(aba.recuperacoes) > 3:
            aba.lbl_espera.configure(text="A página travou várias vezes.\nDigite outro endereço ou use ◀ Voltar.")
            self._log("⚠ A aba travou 4 vezes em 1 minuto: parei de recriá-la. Digite outro endereço.")
            return
        self._sincronizar_barra()
        self.after(150, lambda a=aba: self._criar_webview(a))

    # ------------------------------------------------ estado visual da barra
    def _sincronizar_barra(self):
        aba = self.aba_ativa
        if aba is None:
            return
        if not self.editando_url:
            self._definir_entry(aba.url if aba.url else "")
        self._atualizar_seguranca()
        self._atualizar_estrela()
        self._atualizar_zoom_label()
        self._atualizar_botao_recarregar()
        self._atualizar_nav_botoes()
        self._atualizar_chips()

    def _atualizar_seguranca(self):
        c = _cores()
        u = self.url_atual
        if _eh_site_estrito(u):
            txt, cor = "🛡", c["teal"]
        elif u.startswith("https://"):
            txt, cor = "🔒", c["texto2"]
        elif u.startswith("http://"):
            txt, cor = "⚠", c["perigo"]
        else:
            txt, cor = "🔍", c["texto2"]
        self.lbl_seguranca.configure(text=txt, fg=cor)

    def _atualizar_estrela(self):
        c = _cores()
        u = self.url_atual
        fav = _url_navegavel(u) and self.favoritos.eh_favorito(u)
        self.btn_estrela.configure(text="★" if fav else "☆", fg="#f5b301" if fav else c["texto2"])

    def _atualizar_zoom_label(self):
        aba = self.aba_ativa
        z = aba.zoom if aba else 1.0
        if abs(z - 1.0) > 0.001:
            self.lbl_zoom.configure(text=f"{round(z * 100)}%")
            self.lbl_zoom.pack_forget()
            self.lbl_zoom.pack(side="right", padx=2, after=self.btn_estrela)
        else:
            self.lbl_zoom.pack_forget()

    def _atualizar_botao_recarregar(self):
        aba = self.aba_ativa
        self.btn_recarregar.configure(text="✕" if (aba is not None and aba.carregando) else "⟳")

    def _atualizar_nav_botoes(self):
        c = _cores()
        pode_v = pode_f = True
        try:
            wv = self._wv()
            if wv is not None:
                pode_v, pode_f = bool(wv.can_go_back()), bool(wv.can_go_forward())
        except Exception:
            pass
        self.btn_voltar.configure(fg=c["texto"] if pode_v else c["desab"])
        self.btn_avancar.configure(fg=c["texto"] if pode_f else c["desab"])

    # ---------------------------------------------------------------- histórico
    def _agendar_historico(self, aba):
        if aba.anonima or not _url_navegavel(aba.url):
            return
        if aba.hist_after:
            try:
                self.after_cancel(aba.hist_after)
            except Exception:
                pass
        aba.hist_after = self.after(1500, lambda a=aba, u=aba.url: self._gravar_historico(a, u))

    def _gravar_historico(self, aba, url):
        aba.hist_after = None
        if aba.fechada or aba.url != url or aba.anonima:
            return
        self.historico.registrar(url, aba.titulo)
        self._agendar_salvar()

    def _agendar_salvar(self):
        if self._salvar_after is None:
            self._salvar_after = self.after(2500, self._salvar_agora)

    def _salvar_agora(self):
        self._salvar_after = None
        self.historico.salvar()

    # ---------------------------------------------------------------- favoritos
    def favoritar_pagina(self):
        aba = self.aba_ativa
        if aba is None or not _url_navegavel(aba.url):
            self._log("ℹ Abra uma página (http/https) para poder favoritá-la")
            return
        url = aba.url
        novo = self.favoritos.achar_por_url(url) is None
        titulo = (aba.titulo or _host_de(url).replace("www.", "") or url).strip()
        if novo:
            self.favoritos.adicionar(url, titulo, "barra")
            self.favoritos.salvar()
            self._favoritos_mudaram()
        self._abrir_janela("estrela", lambda nav: _PopupFavorito(nav, url, titulo, novo))

    def _favoritos_mudaram(self):
        self._reconstruir_barra_favoritos()
        self._atualizar_estrela()

    def _aplicar_visibilidade_barra(self):
        if self._var_barra.get() != bool(self.cfg.get("barra_favoritos")):
            self._var_barra.set(bool(self.cfg.get("barra_favoritos")))
        if self.cfg.get("barra_favoritos"):
            self.barra_fav.pack(fill="x", pady=(4, 0))
            self._agendar_layout_fav()
        else:
            self.barra_fav.pack_forget()

    def alternar_barra_favoritos(self):
        self.cfg.set("barra_favoritos", not bool(self.cfg.get("barra_favoritos")))
        self._aplicar_visibilidade_barra()

    def _agendar_layout_fav(self):
        if self._layout_fav_after:
            try:
                self.after_cancel(self._layout_fav_after)
            except Exception:
                pass
        self._layout_fav_after = self.after(90, self._ajustar_barra_fav)

    def _preencher_menu_favoritos(self, menu, lista):
        if not lista:
            menu.add_command(label="(vazia)", state="disabled")
        for no in lista:
            rot = no["titulo"] if len(no["titulo"]) <= 50 else no["titulo"][:49] + "…"
            if no["tipo"] == "link":
                menu.add_command(label="⭐ " + rot, command=lambda u=no["url"]: self.navegar_para(u))
            else:
                sub = _menu_tema(menu)
                self._preencher_menu_favoritos(sub, no["filhos"])
                menu.add_cascade(label="📁 " + rot, menu=sub)

    def _reconstruir_barra_favoritos(self):
        c = _cores()
        for w in self.barra_fav.winfo_children():
            w.destroy()
        self._itens_fav = []
        self.barra_fav.configure(bg=c["fundo"])
        estilo = dict(font=("Segoe UI", 9), relief="flat", bd=0, padx=8, pady=2, bg=c["fundo"], fg=c["texto"],
                      activebackground=c["hover"], activeforeground=c["texto"], cursor="hand2")

        self.mb_outros = tk.Menubutton(self.barra_fav, text="📂 Outros favoritos", **estilo)
        self.mb_outros.pack(side="right")
        m_outros = _menu_tema(self.mb_outros)
        self._preencher_menu_favoritos(m_outros, self.favoritos.raizes["outros"])
        self.mb_outros.configure(menu=m_outros)

        self.mb_mais = tk.Menubutton(self.barra_fav, text="»", **estilo)
        self._menu_mais = _menu_tema(self.mb_mais)
        self.mb_mais.configure(menu=self._menu_mais)

        for no in self.favoritos.raizes["barra"]:
            rot = no["titulo"] if len(no["titulo"]) <= 22 else no["titulo"][:21] + "…"
            if no["tipo"] == "link":
                b = tk.Button(self.barra_fav, text=rot, command=lambda u=no["url"]: self.navegar_para(u), **estilo)
                b.bind("<Button-2>", lambda e, u=no["url"]: self.nova_aba(u))
                b.bind("<Button-3>", lambda e, n=no: self._menu_item_favorito(e, n))
                ToolTip(b, f'{no["titulo"]}\n{no["url"]}')
            else:
                b = tk.Menubutton(self.barra_fav, text="📁 " + rot, **estilo)
                m = _menu_tema(b)
                self._preencher_menu_favoritos(m, no["filhos"])
                b.configure(menu=m)
                b.bind("<Button-3>", lambda e, n=no: self._menu_item_favorito(e, n))
            self._itens_fav.append((b, no))
        self._agendar_layout_fav()

    def _ajustar_barra_fav(self):
        self._layout_fav_after = None
        try:
            if not self.cfg.get("barra_favoritos"):
                return
            total = self.barra_fav.winfo_width()
            if total < 60:
                return
            disp = total - self.mb_outros.winfo_reqwidth() - self.mb_mais.winfo_reqwidth() - 12
            for b, _n in self._itens_fav:
                b.pack_forget()
            self.mb_mais.pack_forget()
            usado, escondidos = 0, []
            for b, no in self._itens_fav:
                larg = b.winfo_reqwidth() + 3
                if usado + larg <= disp and not escondidos:
                    b.pack(side="left", padx=(0, 2))
                    usado += larg
                else:
                    escondidos.append(no)
            if escondidos:
                self._menu_mais.delete(0, tk.END)
                self._preencher_menu_favoritos(self._menu_mais, escondidos)
                self.mb_mais.pack(side="right")
        except tk.TclError:
            pass

    def _menu_item_favorito(self, ev, no):
        m = _menu_tema(self)
        if no["tipo"] == "link":
            m.add_command(label="Abrir", command=lambda: self.navegar_para(no["url"]))
            m.add_command(label="Abrir em nova aba", command=lambda: self.nova_aba(no["url"]))
            m.add_separator()
        m.add_command(label="Editar…", command=lambda: self._editar_favorito(no))
        m.add_command(label="Excluir", command=lambda: self._excluir_favorito(no))
        m.add_separator()
        m.add_command(label="Gerenciar favoritos…", command=self.abrir_gerenciador_favoritos)
        m.tk_popup(ev.x_root, ev.y_root)
        return "break"

    def _editar_favorito(self, no):
        r = _dialogo_editar(self.winfo_toplevel(), "Editar favorito", no["titulo"], no.get("url") if no["tipo"] == "link" else None)
        if r:
            self.favoritos.editar(no["id"], titulo=r[0], url=r[1])
            self.favoritos.salvar()
            self._favoritos_mudaram()

    def _excluir_favorito(self, no):
        self.favoritos.remover(no["id"])
        self.favoritos.salvar()
        self._favoritos_mudaram()

    # --------------------------------------------------------------------- zoom
    def _chave_zoom(self, url):
        return _host_de(url).replace("www.", "")

    def _aplicar_zoom(self, aba):
        z = 1.0
        if _url_navegavel(aba.url):
            try:
                z = float(self.cfg.get("zoom_sites").get(self._chave_zoom(aba.url), 1.0))
            except Exception:
                z = 1.0
        aba.zoom = z
        wv = self._wv(aba)
        if wv is not None and aba.zoom_aplicado != z:
            try:
                wv.set_zoom(z)
                aba.zoom_aplicado = z
            except Exception:
                pass
        if aba is self.aba_ativa:
            self._atualizar_zoom_label()

    def _mudar_zoom(self, direcao):
        aba = self.aba_ativa
        if aba is None or not _url_navegavel(aba.url):
            return
        atual = aba.zoom
        if direcao == 0:
            novo = 1.0
        elif direcao > 0:
            novo = next((p for p in _PASSOS_ZOOM if p > atual + 1e-6), _PASSOS_ZOOM[-1])
        else:
            novo = next((p for p in reversed(_PASSOS_ZOOM) if p < atual - 1e-6), _PASSOS_ZOOM[0])
        chave = self._chave_zoom(aba.url)
        zs = dict(self.cfg.get("zoom_sites"))
        if abs(novo - 1.0) < 1e-6:
            zs.pop(chave, None)
        else:
            zs[chave] = novo
        self.cfg.set("zoom_sites", zs)
        for a in self.abas:
            if _url_navegavel(a.url) and self._chave_zoom(a.url) == chave:
                a.zoom_aplicado = None
                self._aplicar_zoom(a)

    # -------------------------------------------------------- localizar na página
    def abrir_busca(self):
        c = _cores()
        if self.barra_busca is None:
            b = self.barra_busca = tk.Frame(self.slot_busca, bg=c["fundo"])
            tk.Label(b, text="Localizar:", bg=c["fundo"], fg=c["texto"], font=("Segoe UI", 9)).pack(side="left", padx=(2, 4))
            self.var_busca = tk.StringVar()
            self.e_busca = tk.Entry(b, textvariable=self.var_busca, font=("Segoe UI", 10), width=28, relief="solid",
                                    bd=1, bg=c["campo"], fg=c["texto"], insertbackground=c["texto"])
            self.e_busca.pack(side="left", ipady=2)
            self.var_caso = tk.BooleanVar(value=False)
            tk.Checkbutton(b, text="Aa", variable=self.var_caso, command=lambda: self._buscar_na_pagina(False, True),
                           bg=c["fundo"], fg=c["texto"], selectcolor=c["campo"], activebackground=c["fundo"],
                           font=("Segoe UI", 9)).pack(side="left", padx=4)
            for txt, tras in (("▲", True), ("▼", False)):
                _botao_nav(b, txt, lambda t=tras: self._buscar_na_pagina(t)).pack(side="left", padx=1)
            self.lbl_achados = tk.Label(b, text="", bg=c["fundo"], fg=c["texto2"], font=("Segoe UI", 9))
            self.lbl_achados.pack(side="left", padx=8)
            _botao_nav(b, "✕", self._fechar_busca).pack(side="right", padx=2)
            self.e_busca.bind("<Return>", lambda e: (self._buscar_na_pagina(False), "break")[1])
            self.e_busca.bind("<Shift-Return>", lambda e: (self._buscar_na_pagina(True), "break")[1])
            self.e_busca.bind("<Escape>", lambda e: (self._fechar_busca(), "break")[1])
            self.e_busca.bind("<KeyRelease>", self._ao_digitar_busca)
        self.barra_busca.configure(bg=c["fundo"])
        self.barra_busca.pack(fill="x", pady=(4, 0))
        self.e_busca.focus_force()
        self.e_busca.select_range(0, tk.END)
        if self.var_busca.get():
            self._buscar_na_pagina(False, True)

    def _ao_digitar_busca(self, ev):
        if ev.keysym in ("Return", "Escape", "Shift_L", "Shift_R", "Control_L", "Control_R", "Tab"):
            return
        self._buscar_na_pagina(False, True)

    def _fechar_busca(self):
        if self.barra_busca is None or not self.barra_busca.winfo_ismapped():
            return
        wv = self._wv()
        if wv is not None:
            try:
                wv.eval_js("try{window.getSelection().removeAllRanges()}catch(e){}")
            except Exception:
                pass
        self.barra_busca.pack_forget()

    def _buscar_na_pagina(self, tras=False, novo=False):
        wv = self._wv()
        texto = self.var_busca.get()
        if wv is None:
            return
        if not texto:
            self.lbl_achados.configure(text="")
            return
        caso = "true" if self.var_caso.get() else "false"
        q = json.dumps(texto)
        try:
            if novo:
                wv.eval_js("try{window.getSelection().removeAllRanges()}catch(e){}")
            wv.eval_js(f"(function(){{try{{window.find({q},{caso},{'true' if tras else 'false'},true,false,false,false)}}catch(e){{}}}})()")
            contar = (f"(function(q,cs){{var n=0,w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null),"
                      f"t;if(!cs)q=q.toLowerCase();while((t=w.nextNode())){{var s=cs?t.nodeValue:t.nodeValue.toLowerCase(),"
                      f"i=0;while((i=s.indexOf(q,i))!==-1){{n++;i+=q.length}}}}return String(n)}})({q},{caso})")
            wv.eval_js_with_callback(contar, self._mostrar_achados, on_error=lambda e: None)
        except Exception:
            pass

    def _mostrar_achados(self, resultado):
        try:
            n = int(str(resultado).strip().strip('"'))
            self.lbl_achados.configure(text="nenhum resultado" if n == 0 else f"{n} resultado{'s' if n != 1 else ''}")
        except Exception:
            pass

    # ------------------------------------------------------------ menu principal
    def abrir_menu_principal(self):
        m = _menu_tema(self)
        aba = self.aba_ativa
        m.add_command(label="Nova aba", accelerator="Ctrl+T", command=lambda: self.nova_aba())
        m.add_command(label="Nova aba anônima", accelerator="Ctrl+Shift+N", command=lambda: self.nova_aba(anonima=True))
        m.add_command(label="Reabrir aba fechada", accelerator="Ctrl+Shift+T", command=self.reabrir_aba,
                      state="normal" if self._fechadas else "disabled")
        m.add_separator()
        m.add_command(label="Histórico", accelerator="Ctrl+H", command=self.abrir_historico)
        fav = _menu_tema(m)
        fav.add_command(label="Favoritar esta página", accelerator="Ctrl+D", command=self.favoritar_pagina)
        fav.add_command(label="Gerenciar favoritos…", accelerator="Ctrl+Shift+O", command=self.abrir_gerenciador_favoritos)
        fav.add_checkbutton(label="Mostrar barra de favoritos", accelerator="Ctrl+Shift+B",
                            variable=self._var_barra, command=self.alternar_barra_favoritos)
        fav.add_separator()
        self._preencher_menu_favoritos(fav, self.favoritos.raizes["barra"])
        m.add_cascade(label="Favoritos", menu=fav)
        m.add_command(label="Downloads", accelerator="Ctrl+J", command=self.abrir_downloads)
        m.add_separator()
        z = _menu_tema(m)
        z.add_command(label="Aumentar", accelerator="Ctrl++", command=lambda: self._mudar_zoom(1))
        z.add_command(label="Diminuir", accelerator="Ctrl+-", command=lambda: self._mudar_zoom(-1))
        z.add_command(label="Restaurar (100%)", accelerator="Ctrl+0", command=lambda: self._mudar_zoom(0))
        m.add_cascade(label=f"Zoom ({round((aba.zoom if aba else 1) * 100)}%)", menu=z)
        m.add_command(label="Localizar na página…", accelerator="Ctrl+F", command=self.abrir_busca)
        m.add_command(label="Imprimir…", command=self.imprimir)
        m.add_command(label="Ferramentas do desenvolvedor", accelerator="F12", command=self.abrir_devtools)
        m.add_separator()
        m.add_command(label="Copiar endereço da página", command=self.copiar_endereco)
        m.add_command(label="Abrir no navegador do sistema", command=self.abrir_no_navegador_sistema)
        m.add_separator()
        m.add_command(label="Tela cheia do app", accelerator="F11", command=self.alternar_fullscreen)
        m.add_command(label="Limpar dados de navegação…", command=lambda: self.dialogo_limpar_dados(self.winfo_toplevel()))
        if self.menu_extra:   # [Assistir] itens extras (botões de sites, tema, downloads)
            m.add_separator()
            for rot, cmd in self.menu_extra():
                m.add_command(label=rot, command=cmd)
        m.add_command(label="Configurações…", command=self.abrir_config)
        x, y = self.btn_menu.winfo_rootx(), self.btn_menu.winfo_rooty() + self.btn_menu.winfo_height()
        m.tk_popup(x, y)

    def imprimir(self):
        wv = self._wv()
        if wv is not None:
            try:
                wv.print()
            except Exception as e:
                self._log(f"❌ Não foi possível imprimir: {e}")

    def abrir_devtools(self):
        wv = self._wv()
        if wv is not None:
            try:
                wv.open_devtools()
            except Exception as e:
                self._log(f"❌ Não foi possível abrir as ferramentas do desenvolvedor: {e}")

    def copiar_endereco(self):
        u = self.url_atual
        if u:
            self.clipboard_clear()
            self.clipboard_append(u)
            self._log("📋 Endereço copiado")

    def abrir_no_navegador_sistema(self):
        u = self.url_atual
        if _url_navegavel(u):
            webbrowser.open(u)

    def _abrir_no_sistema(self, caminho):
        try:
            if os.name == "nt":
                os.startfile(caminho)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", caminho])
            else:
                subprocess.Popen(["xdg-open", caminho])
        except Exception as e:
            self._log(f"❌ Não foi possível abrir: {e}")

    def _mostrar_na_pasta(self, caminho):
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(caminho)])
            else:
                self._abrir_no_sistema(os.path.dirname(caminho))
        except Exception as e:
            self._log(f"❌ Não foi possível abrir a pasta: {e}")

    # ------------------------------------------------------------------ janelas
    def _abrir_janela(self, chave, fabrica):
        j = self._janelas.get(chave)
        try:
            if j is not None and j.winfo_exists():
                j.deiconify()
                j.lift()
                j.focus_force()
                return j
        except Exception:
            pass
        j = fabrica(self)
        self._janelas[chave] = j
        return j

    def abrir_historico(self):
        return self._abrir_janela("historico", _JanelaHistorico)

    def abrir_gerenciador_favoritos(self):
        return self._abrir_janela("favoritos", _JanelaFavoritos)

    def abrir_downloads(self):
        return self._abrir_janela("downloads", _JanelaDownloads)

    def abrir_config(self):
        return self._abrir_janela("config", _JanelaConfig)

    def dialogo_limpar_dados(self, pai):
        return _JanelaLimparDados(self, pai)

    def _limpar_dados_sites(self):
        for a in self.abas:
            wv = self._wv(a)
            if wv is not None and not a.anonima:
                try:
                    wv.clear_all_browsing_data()
                    return True
                except Exception as e:
                    self._log(f"❌ Não foi possível limpar os dados dos sites: {e}")
                    return False
        self._log("⚠ Nenhuma aba normal pronta para limpar os dados dos sites")
        return False

    # --------------------------------------------------------------- encerramento
    def fechar(self):
        try:
            urls = [a.url for a in self.abas if not a.anonima and _url_navegavel(a.url)]
            ativa = 0
            if self.aba_ativa in self.abas and not self.aba_ativa.anonima and _url_navegavel(self.aba_ativa.url):
                ativa = urls.index(self.aba_ativa.url) if self.aba_ativa.url in urls else 0
            self.cfg.dados["sessao"] = {"urls": urls[:20], "ativa": ativa}
            self.cfg.salvar()
            self.historico.salvar()
            self.favoritos.salvar()
        except Exception:
            pass
        for a in list(self.abas):
            a.fechada = True
            if a.webview is not None:
                try:
                    a.webview.destroy()
                except Exception:
                    pass
                a.webview = None
        for s in (self._sessao_anonima, self._sessao_normal):
            if s is not None:
                try:
                    s.close()
                except Exception:
                    pass
        self._sessao_anonima = self._sessao_normal = None


_FH_ARQUIVO = None
_JS_LIMPAR_CMD = (
    r"(function(){try{var u=location.href.replace(/[#&]?__youdown_cmd__=[a-z0-9_]+\.\d+/g,'').replace(/#$/,'');"
    r"history.replaceState(history.state,'',u)}catch(e){try{location.hash=''}catch(x){}}})()"
)


# ---------------------------------------------------------------------------
# Troca de tema (claro/escuro) em tempo de execução
# ---------------------------------------------------------------------------
_CHAVES_BG = ("BG_SIDEBAR", "BG_EDITOR", "BG_OUTPUT", "BORDER", "BORDER_DARK", "BG_NEUTRO")
_CHAVES_FG = ("FG_EDITOR", "FG_SIDEBAR", "TEAL_TEXTO", "TEXTO_ESPERA", "PERIGO_TEXTO")
_OPCOES_BG = ("bg", "highlightbackground", "highlightcolor", "activebackground")
_OPCOES_FG = ("fg", "insertbackground", "activeforeground")


def _mapas_de_cor(de, para):
    a, b = ArduinoTheme.TEMAS[de], ArduinoTheme.TEMAS[para]
    mapa_bg = {a[k].lower(): b[k] for k in _CHAVES_BG}
    mapa_bg["white"] = b["BG_EDITOR"]
    mapa_fg = {a[k].lower(): b[k] for k in _CHAVES_FG}
    return mapa_bg, mapa_fg


def _recolorir(widget, mapa_bg, mapa_fg):
    for opcoes, mapa in ((_OPCOES_BG, mapa_bg), (_OPCOES_FG, mapa_fg)):
        for opt in opcoes:
            try:
                atual = str(widget.cget(opt)).lower()
            except tk.TclError:
                continue
            novo = mapa.get(atual)
            if not novo: continue
            try:
                widget.configure(**{opt: novo})
            except tk.TclError:
                continue

    if isinstance(widget, BotaoArduino):
        widget.aplicar_tema()
        return

    for filho in widget.winfo_children():
        if isinstance(filho, tk.Toplevel):
            continue
        _recolorir(filho, mapa_bg, mapa_fg)



JS_FS_LIMPAR = r"""
                (function(){
                  try {
                    if (typeof _ydUltimoEstadoFs !== 'undefined') _ydUltimoEstadoFs = false;
                    if (document.fullscreenElement || document.webkitFullscreenElement) {
                      if (document.exitFullscreen) document.exitFullscreen();
                      else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
                    }

                    var h = window.location.hash || '';
                    if (h.indexOf('__youdown_fs_') !== -1) {
                      window.location.hash = h.replace(/&?__youdown_fs_[a-zA-Z0-9_]+__=\d+/g, '').replace(/^#$/, '');
                    }

                    var ytPlayer = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
                    if (ytPlayer) {
                      if (ytPlayer.classList && ytPlayer.classList.contains('ytp-fullscreen')) {
                        try {
                          if (typeof ytPlayer.toggleFullscreen === 'function') ytPlayer.toggleFullscreen();
                        } catch(ex) {}
                        ytPlayer.classList.remove('ytp-fullscreen');
                      }
                    }

                    var vjsElements = document.querySelectorAll('.vjs-fullscreen, .video-js.vjs-fullscreen');
                    for (var i = 0; i < vjsElements.length; i++) {
                      vjsElements[i].classList.remove('vjs-fullscreen');
                    }
                  } catch(e) {}
                })();
                """

# ===========================================================================
# ASSISTIR: botões de sites + janela principal (o navegador acima vem do YouDown, sem alterações
# de comportamento; os poucos ganchos novos estão marcados no próprio código da classe)
# ===========================================================================
_SEGUNDO_NIVEL = {"com", "net", "org", "gov", "edu", "co"}
_NOMES_AMIGAVEIS = {
    "youtube": "YouTube", "redecanais": "RedeCanais", "pobreflix": "PobreFlix", "netflix": "Netflix",
    "globoplay": "GloboPlay", "primevideo": "PrimeVideo", "twitch": "Twitch", "google": "Google",
}
C_BOTAO = "#1F6F78"
C_BOTAO_HOVER = "#2A8D98"
C_EDITAR = "#B8610F"
C_EDITAR_HOVER = "#D27A22"


def host_de(url):
    resto = str(url).split("://", 1)[-1]
    h = re.split(r"[/?#]", resto, 1)[0]
    return h.rsplit("@", 1)[-1].split(":", 1)[0].lower()


def rotulo(host):
    p = [x for x in host.split(".") if x]
    if len(p) >= 3 and len(p[-1]) == 2 and p[-2] in _SEGUNDO_NIVEL:
        return p[-3]
    return p[-2] if len(p) >= 2 else host


def sufixo(host):
    p = [x for x in host.split(".") if x]
    if len(p) >= 3 and len(p[-1]) == 2 and p[-2] in _SEGUNDO_NIVEL:
        return "." + p[-2] + "." + p[-1]
    return "." + p[-1] if len(p) >= 2 else ""


def eh_http(url):
    return str(url).lower().startswith(("http://", "https://"))


def raiz(url):
    esq = "http" if str(url).lower().startswith("http://") else "https"
    return f"{esq}://{host_de(url)}"


def chave_site(url):
    h = host_de(url)
    return h[4:] if h.startswith("www.") else h


def abreviar(url):
    """Nome curto do botão: (nome, sufixo). redecanais.by -> ('RedeCanais', '.by')."""
    host = host_de(url)
    for pre in ("www.", "m."):
        if host.startswith(pre):
            host = host[len(pre):]
    r = rotulo(host)
    nome = _NOMES_AMIGAVEIS.get(r.lower())
    if nome is None:
        limpo = "".join(c for c in r if c.isalnum() or c == "-") or host
        curto = limpo[:9]
        nome = curto[:1].upper() + curto[1:]
    return (nome, sufixo(host))


class Atalho:
    def __init__(self, id_, nome, url, auto=True):
        self.id, self.nome, self.url, self.auto = id_, nome, url, auto

    @property
    def sufixo(self):
        h = host_de(self.url)
        for pre in ("www.", "m."):
            if h.startswith(pre):
                h = h[len(pre):]
        return sufixo(h)

    def __repr__(self):
        return f"Atalho({self.id}, {self.nome!r}, {self.url!r}, auto={self.auto})"


class ListaAtalhos:
    """Os botões de sites. Cada alteração é salva na hora."""

    def __init__(self, caminho):
        self.caminho = caminho
        self.itens = []
        self._proximo = 1
        self._carregar()

    def _carregar(self):
        dados = _ler_json(self.caminho, {})
        itens = dados.get("itens", []) if isinstance(dados, dict) else []
        for d in itens:
            try:
                id_, url = int(d["id"]), str(d["url"])
            except Exception:
                continue
            if not eh_http(url):
                continue
            self.itens.append(Atalho(id_, str(d.get("nome") or abreviar(url)[0]), url, bool(d.get("auto", True))))
            self._proximo = max(self._proximo, id_ + 1)

    def _salvar(self):
        _gravar_json(self.caminho, {"v": 1, "itens": [
            {"id": a.id, "nome": a.nome, "url": a.url, "auto": a.auto} for a in self.itens]})

    def achar(self, id_):
        return next((a for a in self.itens if a.id == id_), None)

    def achar_por_url(self, url):
        ch = chave_site(url)
        if not ch:
            return None
        return next((a for a in self.itens if chave_site(a.url) == ch), None)

    def adicionar_se_novo(self, url):
        """Cria o botão do site se ainda não existir. Retorna o botão novo, ou None se já havia."""
        if not eh_http(url) or not host_de(url):
            return None
        if self.achar_por_url(url) is not None:
            return None
        r = raiz(url)
        a = Atalho(self._proximo, abreviar(r)[0], r, True)
        self._proximo += 1
        self.itens.append(a)
        self._salvar()
        return a

    def remover(self, id_):
        antes = len(self.itens)
        self.itens = [a for a in self.itens if a.id != id_]
        ok = len(self.itens) != antes
        if ok:
            self._salvar()
        return ok

    def editar_endereco(self, id_, nova_url):
        """Troca o endereço do botão (o Redecanais muda de endereço de vez em quando)."""
        a = self.achar(id_)
        if a is None or not eh_http(nova_url) or not host_de(nova_url):
            return False
        a.url = raiz(nova_url)
        if a.auto:
            a.nome = abreviar(a.url)[0]
        self._salvar()
        return True

    def renomear(self, id_, novo_nome):
        a = self.achar(id_)
        n = (novo_nome or "").strip()
        if a is None or not n:
            return False
        a.nome = n[:14]
        a.auto = False
        self._salvar()
        return True


class ConfigAssistir:
    PADRAO = {"tema": "escuro", "bloquear_downloads": False}

    def __init__(self, caminho):
        self.caminho = caminho
        self.dados = dict(self.PADRAO)
        salvo = _ler_json(caminho, {})
        if isinstance(salvo, dict):
            for k, v in self.PADRAO.items():
                if isinstance(salvo.get(k), type(v)):
                    self.dados[k] = salvo[k]

    def get(self, k):
        return self.dados.get(k, self.PADRAO.get(k))

    def set(self, k, v):
        self.dados[k] = v
        _gravar_json(self.caminho, self.dados)


_INIT_JS_BASE = INIT_JS   # script do navegador (AdBlock + atalhos + banners); as regras do usuário entram na frente


def _decodificar_json_duplo(resultado):
    """eval_js_with_callback devolve o resultado como JSON; uma string JSON vem 'dobrada'."""
    try:
        d = json.loads(resultado)
        if isinstance(d, str):
            d = json.loads(d)
        return d
    except Exception:
        return None


class RegrasUsuario:
    """Anúncios que o usuário bloqueou com o conta-gotas: seletores por site e anunciantes (valem em todos)."""

    def __init__(self, caminho):
        self.caminho = caminho
        self.sites = {}
        self.hosts = []
        d = _ler_json(caminho, {})
        if isinstance(d, dict):
            for k, v in (d.get("sites") or {}).items():
                if isinstance(v, list):
                    sels = [x for x in v if self._sel_ok(x)]
                    if sels:
                        self.sites[str(k)] = sels
            self.hosts = [h for h in (d.get("hosts") or []) if self._host_ok(h)]

    @staticmethod
    def _sel_ok(s):
        return isinstance(s, str) and 1 <= len(s) <= 300 and "\n" not in s

    @staticmethod
    def _host_ok(h):
        return isinstance(h, str) and re.fullmatch(r"[a-z0-9][a-z0-9.\-]{2,80}", h) is not None

    @staticmethod
    def chave(url):
        return rotulo(host_de(url))

    def salvar(self):
        _gravar_json(self.caminho, {"v": 1, "sites": self.sites, "hosts": self.hosts})

    def adicionar(self, url_pagina, sel, host):
        """Retorna True se algo novo foi guardado."""
        novo = False
        ch = self.chave(url_pagina)
        if sel and ch and self._sel_ok(sel):
            lista = self.sites.setdefault(ch, [])
            if sel not in lista:
                lista.append(sel)
                novo = True
        h = (host or "").strip().lower()
        if h and self._host_ok(h) and h not in self.hosts:
            self.hosts.append(h)
            novo = True
        if novo:
            self.salvar()
        return novo

    def itens(self):
        """[(escopo, tipo, valor)] para a janela de gerenciamento."""
        saida = [(ch, "Seletor", sel) for ch, lista in self.sites.items() for sel in lista]
        saida += [("(todos os sites)", "Anunciante", h) for h in self.hosts]
        return saida

    def remover(self, escopo, tipo, valor):
        ok = False
        if tipo == "Anunciante" and valor in self.hosts:
            self.hosts.remove(valor)
            ok = True
        elif tipo == "Seletor" and valor in self.sites.get(escopo, []):
            self.sites[escopo].remove(valor)
            if not self.sites[escopo]:
                del self.sites[escopo]
            ok = True
        if ok:
            self.salvar()
        return ok

    def limpar(self):
        self.sites, self.hosts = {}, []
        self.salvar()

    def js(self):
        return "window.__ydRegras = " + json.dumps(
            {"sites": {k: {"sel": v} for k, v in self.sites.items()}, "hosts": self.hosts}) + ";"


class FlowFrame(tk.Frame):
    """Distribui os botões em linhas, quebrando quando a janela fica estreita."""

    def __init__(self, master, bg, espaco=6):
        super().__init__(master, bg=bg, height=1)
        self._itens = []
        self._espaco = espaco
        self._depois = None
        self.bind("<Configure>", lambda e: self._agendar())

    def definir(self, widgets):
        for w in self._itens:
            w.destroy()
        self._itens = list(widgets)
        self._agendar()

    def _agendar(self):
        if self._depois:
            try:
                self.after_cancel(self._depois)
            except Exception:
                pass
        self._depois = self.after(40, self._layout)

    def _layout(self):
        self._depois = None
        largura = self.winfo_width()
        if largura < 60:
            largura = max(self.winfo_toplevel().winfo_width() - 24, 600)
        x = y = linha_h = 0
        for w in self._itens:
            w.update_idletasks()
            rw, rh = w.winfo_reqwidth(), w.winfo_reqheight()
            if x > 0 and x + rw > largura:
                x, y, linha_h = 0, y + linha_h + self._espaco, 0
            w.place(x=x, y=y)
            x += rw + self._espaco
            linha_h = max(linha_h, rh)
        self.configure(height=max(1, y + linha_h))


class BotaoSite(tk.Frame):
    """Um botão de site: nome em cima, final do endereço (.by) embaixo."""

    def __init__(self, master, atalho, editar, ao_abrir, ao_menu, ao_nova_aba):
        self._cor = C_EDITAR if editar else C_BOTAO
        self._hover = C_EDITAR_HOVER if editar else C_BOTAO_HOVER
        super().__init__(master, bg=self._cor, cursor="hand2")
        self.atalho = atalho
        self.l1 = tk.Label(self, text=atalho.nome, font=("Segoe UI", 10, "bold"), bg=self._cor, fg="white")
        self.l2 = tk.Label(self, text=atalho.sufixo or " ", font=("Segoe UI", 8), bg=self._cor, fg="#CFE9EC")
        self.l1.pack(padx=14, pady=(4, 0))
        self.l2.pack(padx=14, pady=(0, 4))
        for w in (self, self.l1, self.l2):
            w.bind("<Button-1>", lambda e: ao_abrir(atalho))
            w.bind("<Button-3>", lambda e: ao_menu(e, atalho))
            w.bind("<Button-2>", lambda e: ao_nova_aba(atalho))
            w.bind("<Enter>", lambda e: self._pintar(self._hover))
            w.bind("<Leave>", lambda e: self._pintar(self._cor))

    def _pintar(self, cor):
        for w in (self, self.l1, self.l2):
            w.configure(bg=cor)


class Assistir:
    def __init__(self, root):
        global _app_instancia
        _app_instancia = self
        self.root = root
        self.root.report_callback_exception = lambda exc, val, tb: registrar_falha_fatal(exc, val, tb)
        self.root.title("Assistir")
        try:
            _ico = os.path.join(BASE_DIR, "icone.ico")
            if os.path.isfile(_ico):
                self.root.iconbitmap(default=_ico)
        except Exception:
            pass
        self.root.geometry("1280x760")
        self.root.minsize(900, 560)
        self.root.resizable(True, True)

        self.cfg = ConfigAssistir(os.path.join(_DIR_NAV, "assistir.json"))
        self.lista = ListaAtalhos(os.path.join(_DIR_NAV, "assistir_atalhos.json"))
        self.regras = RegrasUsuario(os.path.join(_DIR_NAV, "assistir_regras.json"))
        self._pick_ativo = False
        self._pick_ate = 0.0
        self._aplicar_init_js()       # as regras salvas já entram no script das páginas novas

        tema = self.cfg.get("tema")
        if tema not in ArduinoTheme.TEMAS:
            tema = "escuro"
        ArduinoTheme.aplicar(tema)
        self.tema_atual = tema
        self.root.configure(bg=ArduinoTheme.BG_SIDEBAR)

        self.estilo = ttk.Style()
        try:
            self.estilo.theme_use("clam")
        except tk.TclError:
            pass
        self._estilizar_combobox()

        self.em_fullscreen = False
        self.navegador_em_fs = False
        self.floating_hud = None
        self._geo_anterior = "1280x760"
        self.modo_editar = False
        self._status_after = None

        self.root.bind("<F11>", lambda e: self._alternar_fs_navegador())
        self.root.bind("<Escape>", lambda e: self._tratar_esc())

        # barra de status (embaixo) e área do navegador
        self.status_bar = tk.Frame(self.root, bg=ArduinoTheme.BG_STATUSBAR, height=22)
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)
        self.lbl_status = tk.Label(self.status_bar, text="", bg=ArduinoTheme.BG_STATUSBAR, fg=ArduinoTheme.FG_STATUS,
                                   font=("Segoe UI", 9), anchor="w", padx=12)
        self.lbl_status.pack(side="left", fill="x", expand=True)

        self.principal = tk.Frame(self.root, bg=ArduinoTheme.BG_SIDEBAR)
        self.principal.pack(side="top", fill="both", expand=True)

        self.navegador = NavegadorSimples(
            self.principal,
            on_url_mudou=lambda url: None,
            on_capturar_url=None,                       # sem o botão "Usar Vídeo no Painel"
            on_fullscreen=self._alternar_fs_navegador,
            bg=ArduinoTheme.BG_SIDEBAR,
        )
        self.navegador.pack(side="left", fill="both", expand=True)
        self.navegador.on_info = self._log_navegador
        self.navegador.on_site_digitado = self._site_digitado
        self.navegador.menu_extra = self._itens_menu_extra
        self.navegador.bloquear_downloads = bool(self.cfg.get("bloquear_downloads"))

        # barra de botões de sites, logo abaixo da barra de endereço
        self.flow = FlowFrame(self.navegador.top, ArduinoTheme.BG_SIDEBAR)
        self.flow.pack(fill="x", pady=(4, 0), after=self.navegador.toolbar)
        self._reconstruir_botoes()

        self.root.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self.log("Assistir pronto. Digite um endereço na barra e tecle Enter: o site vira um botão.", "ok")

    # ------------------------------------------------------------------ mensagens
    def log(self, msg, tag="info"):
        try:
            self._status(str(msg).strip())
        except Exception:
            pass

    def _log_navegador(self, msg):
        self.log(msg)

    def _status(self, texto):
        self.lbl_status.configure(text=texto)
        if self._status_after:
            try:
                self.root.after_cancel(self._status_after)
            except Exception:
                pass
        self._status_after = self.root.after(9000, lambda: self.lbl_status.configure(text=""))

    # ------------------------------------------------------------------ botões de sites
    def _reconstruir_botoes(self):
        self.flow.configure(bg=ArduinoTheme.BG_SIDEBAR)
        botoes = [BotaoSite(self.flow, a, self.modo_editar, self._ao_clicar_botao, self._menu_botao, self._abrir_em_nova_aba)
                  for a in self.lista.itens]
        self.flow.definir(botoes)

    def _site_digitado(self, url):
        """Chamado pelo navegador quando o usuário digita/escolhe um endereço na barra."""
        novo = self.lista.adicionar_se_novo(url)
        if novo:
            self._reconstruir_botoes()
            self.log(f"Botão criado: {novo.nome}{novo.sufixo}", "ok")

    def _ao_clicar_botao(self, atalho):
        if self.modo_editar:
            self._menu_botao(None, atalho)
        else:
            self.navegador.navegar_para(atalho.url)

    def _abrir_em_nova_aba(self, atalho):
        self.navegador.nova_aba(atalho.url)

    def _menu_botao(self, evento, atalho):
        m = _menu_tema(self.root)
        m.add_command(label="Abrir", command=lambda: self.navegador.navegar_para(atalho.url))
        m.add_command(label="Abrir em nova aba", command=lambda: self.navegador.nova_aba(atalho.url))
        m.add_separator()
        m.add_command(label="Editar nome e endereço (o site mudou)…", command=lambda: self._editar(atalho))
        m.add_command(label="Apagar este botão", command=lambda: self._apagar(atalho))
        if evento is not None:
            m.tk_popup(evento.x_root, evento.y_root)
        else:
            m.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def _editar(self, atalho):
        r = _dialogo_editar(self.root, "Editar botão", atalho.nome, atalho.url)
        if not r:
            return
        nome, url = r
        mudou_url = False
        if url:
            tipo, u = _interpretar_entrada(url)
            if tipo != "url":
                messagebox.showwarning("Endereço inválido", "Digite um endereço como redecanais.by", parent=self.root)
            elif raiz(u) != atalho.url and self.lista.editar_endereco(atalho.id, u):
                mudou_url = True
        if nome and nome != atalho.nome:
            self.lista.renomear(atalho.id, nome)
        self._reconstruir_botoes()
        if mudou_url:
            novo = self.lista.achar(atalho.id)
            self.log("Endereço atualizado", "ok")
            if novo:
                self.navegador.navegar_para(novo.url)

    def _apagar(self, atalho):
        if messagebox.askyesno("Apagar botão", f"Apagar o botão “{atalho.nome}{atalho.sufixo}”?", parent=self.root):
            self.lista.remover(atalho.id)
            self._reconstruir_botoes()

    # ------------------------------------------------------------------ itens extras do menu ⋮
    def _itens_menu_extra(self):
        return [
            ("Criar botão do site atual", self._criar_botao_atual),
            (("✓ " if self.modo_editar else "") + "Editar botões (clique abre as opções)", self._alternar_editar),
            (("✓ " if self.cfg.get("bloquear_downloads") else "") + "Bloquear downloads (só assistir)", self._alternar_downloads),
            ("Bloquear um anúncio (clique nele)…", self._iniciar_picker),
            ("Anúncios bloqueados por você…", self._gerenciar_bloqueios),
            ("Alternar tema claro/escuro", self._alternar_tema),
        ]

    def _criar_botao_atual(self):
        url = self.navegador.url_atual
        novo = self.lista.adicionar_se_novo(url)
        if novo:
            self._reconstruir_botoes()
            self.log(f"Botão criado: {novo.nome}{novo.sufixo}", "ok")
        else:
            self.log("Não foi possível criar o botão (já existe ou não é um site)", "warn")

    def _alternar_editar(self):
        self.modo_editar = not self.modo_editar
        self._reconstruir_botoes()
        self.log("Clique num botão para editar ou apagar" if self.modo_editar else "Edição de botões desligada")

    def _alternar_downloads(self):
        novo = not bool(self.cfg.get("bloquear_downloads"))
        self.cfg.set("bloquear_downloads", novo)
        self.navegador.bloquear_downloads = novo
        self.log("Downloads bloqueados (só assistir)" if novo else "Downloads liberados")

    def _alternar_tema(self):
        novo = "claro" if self.tema_atual == "escuro" else "escuro"
        self._aplicar_tema(novo)
        self.cfg.set("tema", novo)

    def _aplicar_tema(self, nome):
        if nome not in ArduinoTheme.TEMAS:
            nome = "escuro"
        antigo = self.tema_atual
        ArduinoTheme.aplicar(nome)
        if nome != antigo:
            mapa_bg, mapa_fg = _mapas_de_cor(antigo, nome)
            _recolorir(self.root, mapa_bg, mapa_fg)
        self.tema_atual = nome
        self._estilizar_combobox()
        self.navegador.reaplicar_tema()
        self.status_bar.configure(bg=ArduinoTheme.BG_STATUSBAR)
        self.lbl_status.configure(bg=ArduinoTheme.BG_STATUSBAR, fg=ArduinoTheme.FG_STATUS)
        self._reconstruir_botoes()

    def _estilizar_combobox(self):
        T = ArduinoTheme
        e = self.estilo
        e.configure("TCombobox", fieldbackground=T.BG_EDITOR, background=T.BG_NEUTRO, foreground=T.FG_EDITOR,
                    arrowcolor=T.FG_EDITOR, bordercolor=T.BORDER_DARK, lightcolor=T.BG_EDITOR, darkcolor=T.BG_EDITOR)
        e.map("TCombobox", fieldbackground=[("readonly", T.BG_EDITOR)], foreground=[("readonly", T.FG_EDITOR)],
              background=[("readonly", T.BG_NEUTRO)], selectbackground=[("readonly", T.BG_EDITOR)],
              selectforeground=[("readonly", T.FG_EDITOR)], bordercolor=[("focus", T.TEAL)])

    # ------------------------------------------------------------------ conta-gotas de anúncios
    def _aplicar_init_js(self, enviar_pagina=False):
        """Atualiza o script injetado nas páginas NOVAS e (opcional) já na página aberta."""
        global INIT_JS
        INIT_JS = self.regras.js() + "\n" + _INIT_JS_BASE
        if enviar_pagina:
            wv = getattr(self, "navegador", None) and self.navegador.webview
            if wv is not None and getattr(wv, "ready", False):
                try:
                    wv.eval_js(self.regras.js())
                except Exception:
                    pass

    def _iniciar_picker(self):
        wv = self.navegador.webview
        if wv is None or not getattr(wv, "ready", False):
            self.log("Abra uma página primeiro.", "warn")
            return
        try:
            wv.eval_js("window.__ydPicker && window.__ydPicker();")
        except Exception as e:
            self.log(f"Não foi possível iniciar o seletor: {e}", "erro")
            return
        self.log("Clique no anúncio que quer bloquear na página (Esc cancela).", "info")
        self._pick_ativo = True
        self._pick_ate = time.time() + 95
        self.root.after(450, self._pick_poll)

    def _pick_poll(self):
        if not self._pick_ativo:
            return
        if time.time() > self._pick_ate:
            self._pick_ativo = False
            return
        wv = self.navegador.webview
        try:
            if wv is not None and getattr(wv, "ready", False):
                wv.eval_js_with_callback("JSON.stringify(window.__ydPick||null)", self._pick_resultado,
                                         on_error=lambda e: None)
        except Exception:
            pass
        self.root.after(450, self._pick_poll)

    def _pick_resultado(self, resultado):
        dados = _decodificar_json_duplo(resultado)
        if not isinstance(dados, dict) or not self._pick_ativo:
            return
        self._pick_ativo = False
        wv = self.navegador.webview
        try:
            if wv is not None:
                wv.eval_js("window.__ydPick = null;")
        except Exception:
            pass
        if dados.get("cancelado"):
            self.log("Seleção cancelada.")
            return
        sel, host = dados.get("sel"), dados.get("host") or ""
        if self.regras.adicionar(self.navegador.url_atual, sel, host):
            self._aplicar_init_js(enviar_pagina=True)
            extra = f" (anunciante {host}: some em todos os sites)" if host else ""
            self.log(f"Anúncio bloqueado{extra}. Fica salvo para as próximas visitas.", "ok")
        else:
            self.log("Esse anúncio já estava bloqueado.")

    def _gerenciar_bloqueios(self):
        j = _JanelaNav(self.navegador, "Anúncios bloqueados por você", 700, 420)
        c = j.c
        tk.Label(j, text="Bloqueios criados com “Bloquear um anúncio”. Remover vale na próxima vez que a página abrir (F5).",
                 bg=c["fundo"], fg=c["texto2"], font=("Segoe UI", 9), anchor="w", wraplength=660,
                 justify="left").pack(fill="x", padx=10, pady=(10, 4))
        corpo = tk.Frame(j, bg=c["fundo"])
        corpo.pack(fill="both", expand=True, padx=10, pady=4)
        arv = ttk.Treeview(corpo, columns=("tipo", "valor"), style=_estilo_arvore(j), selectmode="extended")
        arv.heading("#0", text="Onde vale")
        arv.heading("tipo", text="Tipo")
        arv.heading("valor", text="Valor")
        arv.column("#0", width=140, stretch=False)
        arv.column("tipo", width=100, stretch=False)
        arv.column("valor", width=400)
        sb = ttk.Scrollbar(corpo, orient="vertical", command=arv.yview)
        arv.configure(yscrollcommand=sb.set)
        arv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        mapa = {}

        def preencher():
            arv.delete(*arv.get_children())
            mapa.clear()
            for i, (escopo, tipo, valor) in enumerate(self.regras.itens()):
                iid = f"r{i}"
                mapa[iid] = (escopo, tipo, valor)
                arv.insert("", "end", iid=iid, text=escopo, values=(tipo, valor))
            if not mapa:
                arv.insert("", "end", text="Nenhum bloqueio seu ainda", values=("", ""))

        def remover():
            for iid in arv.selection():
                if iid in mapa:
                    self.regras.remover(*mapa[iid])
            self._aplicar_init_js(enviar_pagina=True)
            preencher()

        def limpar_tudo():
            if messagebox.askyesno("Limpar tudo", "Apagar TODOS os seus bloqueios de anúncios?", parent=j):
                self.regras.limpar()
                self._aplicar_init_js(enviar_pagina=True)
                preencher()

        rodape = tk.Frame(j, bg=c["fundo"])
        rodape.pack(fill="x", padx=10, pady=(4, 10))
        _botao_nav(rodape, "Remover selecionados", remover).pack(side="left", padx=(0, 6))
        _botao_nav(rodape, "Limpar tudo", limpar_tudo).pack(side="left")
        _botao_nav(rodape, "Fechar", j.destroy).pack(side="right")
        preencher()
        j._preencher = preencher
        self._janela_bloqueios = j

    # ------------------------------------------------------------------ tela cheia (igual ao YouDown)
    def _alternar_fullscreen(self):
        if self.em_fullscreen:
            self.root.attributes("-fullscreen", False)
            self.em_fullscreen = False
            try:
                self.root.geometry(self._geo_anterior)
            except Exception:
                self.root.geometry("1280x760")
            return
        try:
            self._geo_anterior = self.root.geometry()
        except Exception:
            pass
        self.root.attributes("-fullscreen", True)
        self.em_fullscreen = True

    def _tratar_esc(self):
        if getattr(self, "navegador_em_fs", False):
            self._sair_fs_navegador()

    def _alternar_fs_navegador(self, estado=None):
        if estado is True:
            self._entrar_fs_navegador()
        elif estado is False:
            self._sair_fs_navegador()
        else:
            if self.navegador_em_fs:
                self._sair_fs_navegador()
            else:
                self._entrar_fs_navegador()

    def _sincronizar_geometria_fs(self):
        try:
            self.root.update_idletasks()
            if hasattr(self, "navegador") and self.navegador:
                if hasattr(self.navegador, "webview") and self.navegador.webview:
                    self.navegador.webview.sync_bounds()
        except Exception:
            pass

    def _forcar_player_fullscreen_js(self, ativar):
        try:
            if not self.navegador or not self.navegador.webview or not self.navegador.webview.ready:
                return
            if ativar:
                js = """
                (function(){
                  try {
                    document.documentElement.style.overflow = 'hidden';
                    document.body.style.overflow = 'hidden';
                    document.body.style.background = '#000';

                    var host = (window.location && window.location.hostname) ? window.location.hostname.toLowerCase() : '';
                    if (host.includes('youtube.com') || host.includes('youtu.be')) {
                      var ytApp = document.querySelector('ytd-app');
                      if (ytApp) ytApp.style.overflow = 'hidden';

                      var stYt = document.getElementById('__youdown_yt_fs_style');
                      if (!stYt) {
                        stYt = document.createElement('style');
                        stYt.id = '__youdown_yt_fs_style';
                        stYt.textContent = `
                          #masthead-container, #secondary, #below, #comments, #chat, ytd-merch-shelf-renderer, #ticker {
                            display: none !important;
                          }
                          ytd-app, ytd-watch-flexy, #page-manager, #columns, #primary, #primary-inner {
                            overflow: hidden !important;
                            margin: 0 !important;
                            padding: 0 !important;
                            max-width: 100vw !important;
                            max-height: 100vh !important;
                            width: 100vw !important;
                            height: 100vh !important;
                          }
                          #player-container, #player-container-outer, #player-container-inner, ytd-player, #container.ytd-player {
                            position: fixed !important;
                            top: 0 !important;
                            left: 0 !important;
                            width: 100vw !important;
                            height: 100vh !important;
                            z-index: 2147483647 !important;
                            background: #000 !important;
                          }
                          #movie_player {
                            position: fixed !important;
                            top: 0 !important;
                            left: 0 !important;
                            width: 100vw !important;
                            height: 100vh !important;
                            z-index: 2147483647 !important;
                            background: #000 !important;
                          }
                          #movie_player video {
                            width: 100% !important;
                            height: 100% !important;
                            object-fit: contain !important;
                          }
                        `;
                        (document.head || document.documentElement).appendChild(stYt);
                      }
                    }

                    var iframes = document.querySelectorAll('iframe');
                    for (var i = 0; i < iframes.length; i++) {
                      var ifr = iframes[i];
                      var isPlayer = (
                        ifr.name === 'Player' ||
                        (ifr.src && (ifr.src.includes('server.php') || ifr.src.includes('embed.php') || ifr.src.includes('player') || ifr.src.includes('video'))) ||
                        ifr.hasAttribute('allowfullscreen') ||
                        ifr.offsetWidth > 300
                      );
                      if (isPlayer) {
                        if (typeof ifr.dataset.__prev_style === 'undefined') {
                          ifr.dataset.__prev_style = ifr.getAttribute('style') || '';
                        }
                        ifr.style.cssText = 'position:fixed !important; top:0 !important; left:0 !important; width:100vw !important; height:100vh !important; z-index:2147483647 !important; background:#000 !important; border:none !important; margin:0 !important; padding:0 !important; max-width:none !important; max-height:none !important; box-shadow:none !important;';
                        try {
                          var doc = ifr.contentDocument || (ifr.contentWindow && ifr.contentWindow.document);
                          if (doc) {
                            doc.documentElement.style.cssText = 'overflow:hidden !important; background:#000 !important; margin:0 !important; padding:0 !important; width:100% !important; height:100% !important;';
                            doc.body.style.cssText = 'overflow:hidden !important; background:#000 !important; margin:0 !important; padding:0 !important; width:100% !important; height:100% !important;';
                            var innerV = doc.querySelector('video');
                            if (innerV) {
                              innerV.style.cssText = 'width:100% !important; height:100% !important; object-fit:contain !important; background:#000 !important;';
                            }
                            var innerP = doc.querySelector('#player, .video-js, [class*="player"]');
                            if (innerP) {
                              innerP.style.cssText = 'width:100% !important; height:100% !important; max-width:none !important; max-height:none !important; position:absolute !important; top:0 !important; left:0 !important; margin:0 !important; padding:0 !important;';
                            }
                          }
                        } catch(innerErr) {}
                        break;
                      }
                    }

                    if (!host.includes('youtube.com') && !host.includes('youtu.be')) {
                      var v = document.querySelector('video');
                      if (v) {
                        if (typeof v.dataset.__prev_style === 'undefined') {
                          v.dataset.__prev_style = v.getAttribute('style') || '';
                        }
                        v.style.cssText = 'position:fixed !important; top:0 !important; left:0 !important; width:100vw !important; height:100vh !important; z-index:2147483647 !important; background:#000 !important; object-fit:contain !important; margin:0 !important;';
                      }
                    }
                  } catch(e) {}
                })();
                """
            else:
                js = """
                (function(){
                  try {
                    document.documentElement.style.overflow = '';
                    document.body.style.overflow = '';
                    document.body.style.background = '';

                    var stYt = document.getElementById('__youdown_yt_fs_style');
                    if (stYt) stYt.remove();

                    var ytApp = document.querySelector('ytd-app');
                    if (ytApp) ytApp.style.overflow = '';

                    var iframes = document.querySelectorAll('iframe');
                    for (var i = 0; i < iframes.length; i++) {
                      var ifr = iframes[i];
                      if (typeof ifr.dataset.__prev_style !== 'undefined') {
                        ifr.style.cssText = ifr.dataset.__prev_style;
                        delete ifr.dataset.__prev_style;
                      } else {
                        ifr.style.position = ''; ifr.style.width = ''; ifr.style.height = ''; ifr.style.zIndex = ''; ifr.style.background = '';
                      }
                      try {
                        var doc = ifr.contentDocument || (ifr.contentWindow && ifr.contentWindow.document);
                        if (doc) {
                          doc.documentElement.style.cssText = '';
                          doc.body.style.cssText = '';
                          var innerV = doc.querySelector('video');
                          if (innerV) innerV.style.cssText = '';
                          var innerP = doc.querySelector('#player, .video-js, [class*="player"]');
                          if (innerP) innerP.style.cssText = '';
                        }
                      } catch(innerErr) {}
                    }

                    var v = document.querySelector('video');
                    if (v && typeof v.dataset.__prev_style !== 'undefined') {
                      v.style.cssText = v.dataset.__prev_style;
                      delete v.dataset.__prev_style;
                    }

                    if (document.fullscreenElement || document.webkitFullscreenElement) {
                      if (document.exitFullscreen) document.exitFullscreen();
                      else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
                    }

                    var ytPlayer = document.getElementById('movie_player') || document.querySelector('.html5-video-player');
                    if (ytPlayer) {
                      if (ytPlayer.classList && ytPlayer.classList.contains('ytp-fullscreen')) {
                        try {
                          if (typeof ytPlayer.toggleFullscreen === 'function') ytPlayer.toggleFullscreen();
                        } catch(ex) {}
                        ytPlayer.classList.remove('ytp-fullscreen');
                      }
                    }

                    var vjsElements = document.querySelectorAll('.vjs-fullscreen, .video-js.vjs-fullscreen');
                    for (var i = 0; i < vjsElements.length; i++) {
                      vjsElements[i].classList.remove('vjs-fullscreen');
                    }
                  } catch(e) {}
                })();
                """
            self.navegador.webview.eval_js(js)
        except Exception:
            pass


    def _entrar_fs_navegador(self):
        if self.navegador_em_fs:
            return
        self.navegador_em_fs = True
        self.navegador.navegador_em_fs = True
        self._app_fs_antes = self.em_fullscreen

        self._bg_root_ant = self.root.cget("bg")
        self._bg_principal_ant = self.principal.cget("bg")
        self._bg_navegador_ant = self.navegador.cget("bg")
        self._bg_container_ant = self.navegador.container.cget("bg")

        # Oculta tudo que não é o vídeo (barra de abas, endereço, botões de sites e barra de status)
        self.status_bar.pack_forget()
        self.navegador.top.pack_forget()

        self.root.configure(bg="black")
        self.principal.configure(bg="black", bd=0, highlightthickness=0)
        self.navegador.configure(bg="black", bd=0, highlightthickness=0)
        self.navegador.container.configure(bg="black", bd=0, highlightthickness=0)

        self.navegador.pack_forget()
        self.navegador.pack(fill="both", expand=True)
        self.navegador.container.pack_configure(padx=0, pady=0)

        if not self.em_fullscreen:
            self._alternar_fullscreen()

        self._sincronizar_geometria_fs()
        self.root.after(40, self._sincronizar_geometria_fs)
        self.root.after(100, self._sincronizar_geometria_fs)
        self.root.after(250, self._sincronizar_geometria_fs)
        self.root.after(500, self._sincronizar_geometria_fs)

        self._forcar_player_fullscreen_js(True)
        self.root.after(150, lambda: self._forcar_player_fullscreen_js(True))
        self.root.after(400, lambda: self._forcar_player_fullscreen_js(True))
        self._criar_hud_fs()

    def _sair_fs_navegador(self):
        if not self.navegador_em_fs:
            return
        self.navegador_em_fs = False
        self.navegador.navegador_em_fs = False
        self.navegador._fs_disparado_por_site = False
        self.navegador._ignorar_fs_ate = time.time() + 2.0

        try:
            if self.navegador and self.navegador.webview and self.navegador.webview.ready:
                self.navegador.webview.eval_js(JS_FS_LIMPAR)
        except Exception:
            pass

        try:
            if self.floating_hud and self.floating_hud.winfo_exists():
                self.floating_hud.destroy()
                self.floating_hud = None
        except Exception:
            pass

        self._forcar_player_fullscreen_js(False)
        self._restaurar_layout_normal()

        if not self._app_fs_antes and self.em_fullscreen:
            self._alternar_fullscreen()

        self._sincronizar_geometria_fs()
        self.root.after(60, self._sincronizar_geometria_fs)
        self.root.after(180, self._sincronizar_geometria_fs)

    def _restaurar_layout_normal(self):
        try:
            self.root.configure(bg=getattr(self, "_bg_root_ant", ArduinoTheme.BG_SIDEBAR))
            self.principal.configure(bg=getattr(self, "_bg_principal_ant", ArduinoTheme.BG_SIDEBAR))
            self.navegador.configure(bg=getattr(self, "_bg_navegador_ant", ArduinoTheme.BG_SIDEBAR))
            self.navegador.container.configure(bg=getattr(self, "_bg_container_ant", "white"))
        except Exception:
            pass

        self.status_bar.pack_forget()
        self.principal.pack_forget()
        self.navegador.pack_forget()

        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)
        self.principal.pack(side="top", fill="both", expand=True)
        self.navegador.pack(side="left", fill="both", expand=True)

        self.navegador.top.pack(fill="x", padx=6, pady=(6, 4), before=self.navegador.container)
        self.navegador.container.pack_configure(padx=6, pady=(0, 6))

    def _criar_hud_fs(self):
        try:
            if self.floating_hud and self.floating_hud.winfo_exists():
                self.floating_hud.destroy()
                self.floating_hud = None
        except Exception:
            pass

        hud = self.floating_hud = tk.Toplevel(self.root)
        hud.overrideredirect(True)
        hud.attributes("-topmost", True)
        hud.attributes("-alpha", 0.85)
        hud.config(bg="#111111")

        btn = tk.Label(hud, text="⛶ Sair da Tela Cheia [Esc]", font=("Segoe UI", 9, "bold"),
                       bg="#111111", fg="#cccccc", padx=10, pady=5, cursor="hand2")
        btn.pack()
        btn.bind("<Button-1>", lambda e: self._sair_fs_navegador())
        hud.bind("<Button-1>", lambda e: self._sair_fs_navegador())
        btn.bind("<Enter>", lambda e: (btn.config(bg="#c0392b", fg="white"), hud.attributes("-alpha", 1.0)))
        btn.bind("<Leave>", lambda e: (btn.config(bg="#111111", fg="#cccccc"), hud.attributes("-alpha", 0.85)))

        hud.update_idletasks()
        w = hud.winfo_reqwidth()
        h = hud.winfo_reqheight()
        sw = hud.winfo_screenwidth()
        hud.geometry(f"{w}x{h}+{sw - w - 24}+16")

        def _auto_ocultar():
            try:
                if hud and hud.winfo_exists():
                    hud.attributes("-alpha", 0.25)
            except Exception:
                pass
        self.root.after(4000, _auto_ocultar)

    # ------------------------------------------------------------------ encerramento
    def _ao_fechar(self):
        try:
            self.navegador.fechar()
        except Exception:
            pass
        try:
            if self.floating_hud and self.floating_hud.winfo_exists():
                self.floating_hud.destroy()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    Assistir(root)
    root.mainloop()


if __name__ == "__main__":
    main()

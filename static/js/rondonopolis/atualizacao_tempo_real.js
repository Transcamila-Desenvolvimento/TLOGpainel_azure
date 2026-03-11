/**
 * Sistema de atualização em tempo real para todas as telas
 * Funciona com WebSocket quando disponível, ou polling como fallback
 */

class AtualizacaoTempoReal {
    constructor(tela, urlAtualizacao, intervaloPolling = 3000) {
        this.tela = tela; // 'portaria', 'checklist', 'armazem', 'onda', 'documentos'
        this.urlAtualizacao = urlAtualizacao;
        this.intervaloPolling = intervaloPolling;
        this.socket = null;
        this.pollingInterval = null;
        this.ultimaAtualizacao = null;
        this.conectado = false;
        
        this.init();
    }
    
    init() {
        // Tentar conectar via WebSocket primeiro
        this.tentarWebSocket();
        
        // Se WebSocket falhar, usar polling
        setTimeout(() => {
            if (!this.conectado) {
                this.iniciarPolling();
            }
        }, 2000);
    }
    
    tentarWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${this.tela}/`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            this.socket.onopen = () => {
                console.log(`WebSocket conectado para ${this.tela}`);
                this.conectado = true;
                // Parar polling se estiver rodando
                if (this.pollingInterval) {
                    clearInterval(this.pollingInterval);
                    this.pollingInterval = null;
                }
            };
            
            this.socket.onmessage = (e) => {
                const data = JSON.parse(e.data);
                this.processarAtualizacao(data);
            };
            
            this.socket.onerror = (e) => {
                console.error(`Erro no WebSocket para ${this.tela}:`, e);
                this.conectado = false;
                // Tentar polling se WebSocket falhar
                if (!this.pollingInterval) {
                    this.iniciarPolling();
                }
            };
            
            this.socket.onclose = () => {
                console.log(`WebSocket desconectado para ${this.tela}. Usando polling...`);
                this.conectado = false;
                // Reconectar após 3 segundos ou usar polling
                setTimeout(() => {
                    if (!this.conectado) {
                        this.iniciarPolling();
                    } else {
                        this.tentarWebSocket();
                    }
                }, 3000);
            };
        } catch (e) {
            console.warn(`WebSocket não disponível para ${this.tela}. Usando polling.`);
            this.iniciarPolling();
        }
    }
    
    iniciarPolling() {
        if (this.pollingInterval) return;
        
        console.log(`Iniciando polling para ${this.tela} a cada ${this.intervaloPolling}ms`);
        
        // Primeira atualização imediata
        this.atualizarViaPolling();
        
        // Depois atualizar periodicamente
        this.pollingInterval = setInterval(() => {
            this.atualizarViaPolling();
        }, this.intervaloPolling);
    }
    
    async atualizarViaPolling() {
        try {
            const response = await fetch(this.urlAtualizacao, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Verificar se há mudanças
                    const timestamp = data.timestamp || Date.now();
                    if (!this.ultimaAtualizacao || timestamp > this.ultimaAtualizacao) {
                        this.ultimaAtualizacao = timestamp;
                        this.processarDadosAtualizados(data);
                    }
                }
            }
        } catch (error) {
            console.error(`Erro ao atualizar ${this.tela} via polling:`, error);
        }
    }
    
    processarAtualizacao(data) {
        // Chamar callback personalizado se existir
        if (typeof this.onAtualizacao === 'function') {
            this.onAtualizacao(data);
        }
    }
    
    processarDadosAtualizados(data) {
        // Chamar callback personalizado se existir
        if (typeof this.onDadosAtualizados === 'function') {
            this.onDadosAtualizados(data);
        }
    }
    
    destruir() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
}

// Exportar para uso global
window.AtualizacaoTempoReal = AtualizacaoTempoReal;


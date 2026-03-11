// Service Worker para Web Push Notifications
console.log('Service Worker carregado e ativo');

self.addEventListener('push', function(event) {
    console.log('🔔 Push notification recebida no Service Worker');
    console.log('Event data:', event.data);
    
    let data = {};
    
    if (event.data) {
        try {
            data = event.data.json();
            console.log('Dados da notificação:', data);
        } catch (e) {
            console.log('Erro ao parsear JSON, usando texto:', e);
            const texto = event.data.text();
            data = {
                title: 'TLOGpainel',
                body: texto || 'Nova atualização disponível',
                icon: '/static/imagens/icone.png'
            };
        }
    } else {
        console.log('Sem dados no evento push');
        data = {
            title: 'TLOGpainel',
            body: 'Nova atualização disponível',
            icon: '/static/imagens/icone.png'
        };
    }
    
    const options = {
        body: data.body || 'Nova atualização disponível',
        icon: data.icon || '/static/imagens/icone.png',
        badge: '/static/imagens/icone.png',
        tag: data.tag || 'tlogpainel-notification',
        requireInteraction: false,
        vibrate: [200, 100, 200],
        data: data.data || {},
        // Garantir que a notificação apareça mesmo com o site fechado
        silent: false
    };
    
    console.log('📢 Mostrando notificação:', data.title, options.body);
    console.log('📢 Opções:', JSON.stringify(options));
    
    event.waitUntil(
        self.registration.showNotification(data.title || 'TLOGpainel', options)
            .then(() => {
                console.log('✅ Notificação exibida com sucesso!');
            })
            .catch((error) => {
                console.error('❌ Erro ao exibir notificação:', error);
                console.error('Detalhes do erro:', error.message, error.stack);
            })
    );
});

// Quando o usuário clica na notificação
self.addEventListener('notificationclick', function(event) {
    console.log('📱 Notificação clicada:', event.notification);
    event.notification.close();
    
    // Pegar a URL da notificação (pode estar em data.url ou na propriedade url)
    const notificationData = event.notification.data || {};
    const url = notificationData.url || event.notification.data?.url || '/';
    
    console.log('🔗 Abrindo URL:', url);
    
    // Abrir ou focar na janela do site
    event.waitUntil(
        clients.matchAll({ 
            type: 'window', 
            includeUncontrolled: true 
        }).then(function(clientList) {
            // Verificar se já existe uma janela aberta com a mesma origem
            for (let i = 0; i < clientList.length; i++) {
                const client = clientList[i];
                // Verificar se é a mesma origem (mesmo domínio)
                try {
                    const clientUrl = new URL(client.url);
                    const targetUrl = new URL(url, self.location.origin);
                    
                    if (clientUrl.origin === targetUrl.origin && 'focus' in client) {
                        // Se a URL é diferente, navegar para a nova URL antes de focar
                        if (client.url !== targetUrl.href) {
                            return client.navigate(targetUrl.href).then(() => client.focus());
                        }
                        return client.focus();
                    }
                } catch (e) {
                    // Se houver erro ao parsear URL, tentar focar mesmo assim
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        return client.focus();
                    }
                }
            }
            
            // Se não existe janela aberta, abrir nova janela com a URL
            if (clients.openWindow) {
                // Garantir que a URL seja absoluta
                const absoluteUrl = url.startsWith('http') ? url : new URL(url, self.location.origin).href;
                console.log('🪟 Abrindo nova janela com URL:', absoluteUrl);
                return clients.openWindow(absoluteUrl);
            }
        }).catch(function(error) {
            console.error('❌ Erro ao abrir janela:', error);
            // Fallback: tentar abrir a URL raiz
            if (clients.openWindow) {
                return clients.openWindow('/');
            }
        })
    );
});


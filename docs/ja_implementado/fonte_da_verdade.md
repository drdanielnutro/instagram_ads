/// Fonte da Verdade – Professor Virtual (v2.0 - Foco na Interação Direta) ///

/// Este documento descreve o comportamento e os fluxos do aplicativo Professor Virtual, focando na experiência do usuário e nas respostas do sistema a ações diretas e pontuais. ///

# Fluxo de Interação Otimizado - Professor Virtual

## Visão Geral

O aplicativo cria uma experiência educacional inteligente e de baixa fricção para crianças. A interação é projetada para ser iniciada por ações claras e intencionais do usuário, garantindo respostas rápidas e contextuais. O sistema ativa recursos avançados, como a análise visual, de forma fluida e apenas quando necessário.

## Fluxo Completo da Interação

### 1. Início da Interação: Ação de Falar
- A criança inicia a interação mantendo um botão de microfone (🎙) pressionado na tela.
- Enquanto o botão está pressionado, o aplicativo captura o áudio da sua dúvida ou problema.
- Ao soltar o botão, a captura de áudio é finalizada.

### 2. Envio e Processamento da Fala
- O arquivo de áudio completo, correspondente à fala da criança, é enviado para processamento central de forma pontual.
- O sistema transcreve o áudio para texto.

### 3. Análise do Conteúdo e Decisão sobre Contexto Visual
- O sistema analisa o texto transcrito para detectar se há referências que sugerem a necessidade de contexto visual (ex: "esse exercício aqui").
- **Se detectada necessidade visual com alta confiança:** O fluxo prossegue para a "Ativação da Câmera".
- **Caso contrário:** O fluxo prossegue diretamente para a "Geração e Apresentação da Resposta".

### 4. Ativação da Câmera (Fluxo Visual)
- O aplicativo **abre a interface da câmera imediatamente**, mostrando o que a câmera está vendo. Não há um pop-up de confirmação prévio.
- A criança tem duas opções diretas na interface da câmera:
    - **Tocar no ícone de captura (📷):** A foto é tirada instantaneamente.
    - **Tocar no ícone de fechar (X):** A interface da câmera é fechada, e o sistema entende que deve prosseguir sem a imagem.
- Não há uma etapa de "preview" da foto. A captura é considerada a confirmação final.

### 5. Envio e Análise da Imagem
- A imagem capturada é enviada imediatamente para análise, **junto com o contexto da pergunta original** que motivou a ativação da câmera.
- O sistema analisa a imagem para extrair informações relevantes.
- **Fallback Inteligente:** Se o sistema julgar a imagem como inadequada (fora de foco, conteúdo não educacional, etc.), ele informará a criança e poderá solicitar uma nova captura.

### 6. Geração e Apresentação da Resposta
- O sistema combina todas as informações disponíveis (texto da pergunta e, se houver, análise da imagem) para gerar uma resposta educativa estruturada.
- A resposta é enviada para o aplicativo primariamente em formato de **texto**, para ser exibida na tela.

### 7. Apresentação da Resposta e Áudio Contextual
- O aplicativo exibe o texto da resposta na tela.
- Simultaneamente, para notificar o usuário, o aplicativo toca um **áudio curto e pré-gravado** (ex: "Prontinho, aqui está sua resposta!").
- Para respostas mais longas ou explicações detalhadas, um **botão de "Play" (▶️) aparece ao lado do texto**.
    - O áudio da explicação completa **só é gerado e reproduzido se a criança tocar neste botão**. Esta é uma funcionalidade sob demanda.

## Pontos-Chave de Comportamento

### Interação Direta e Pontual
- O sistema reage a eventos discretos (soltar o botão de microfone, tocar no botão da câmera), em vez de manter conexões de processamento contínuas.

### Redução de Fricção
- A câmera abre diretamente para minimizar etapas de confirmação.
- O envio da imagem é imediato, com o sistema, e não o usuário, sendo responsável por validar a qualidade da imagem.

### Comunicação Multicanal Otimizada
- O uso de áudios pré-gravados para notificações rápidas e um sistema de Texto-para-Voz (TTS) sob demanda para explicações detalhadas garante uma comunicação eficiente e focada.

### Fallbacks Robustos
- O sistema é projetado para continuar a interação de forma útil mesmo se a captura visual falhar ou for cancelada.

### Privacidade
- O processamento de dados visuais é efêmero e contextual, sem armazenamento permanente.
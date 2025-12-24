---
title: prediction
description:
published: true
date: 2024-12-10T19:52:01.245Z
tags:
editor: markdown
dateCreated: 2024-11-29T15:47:04.302Z
---

# Prediction

# Introdução a Prediction

O módulo de **Prediction** é responsável por estimar o comportamento esperado dos equipamentos a partir de dados históricos e operacionais.  
Ele utiliza modelos estatísticos e de aprendizado de máquina para identificar desvios entre o valor esperado e o valor medido, permitindo a detecção antecipada de anomalias.

O objetivo principal é apoiar estratégias de manutenção preditiva, reduzindo falhas inesperadas e otimizando a disponibilidade dos ativos.

---

# Home

A página inicial de **Prediction** apresenta uma visão consolidada do status preditivo dos dispositivos monitorados.  
Nela é possível visualizar indicadores gerais, como:

- Quantidade de alarmes ativos
- Distribuição de severidade
- Dispositivos com maior recorrência de desvios
- Período mais recente de análise

Essas informações permitem uma avaliação rápida da saúde operacional do parque monitorado.

---

# Prediction Alarms

A seção de **Prediction Alarms** lista todos os alarmes gerados pelos modelos preditivos.  
Cada alarme representa um desvio relevante entre o comportamento esperado e o comportamento observado de uma variável monitorada.

Os alarmes podem ser filtrados por dispositivo, componente, variável, período e status, facilitando a priorização de análises e ações de manutenção.

---

# Prediction Detail

Em **Prediction Detail** são apresentados os detalhes de um alarme específico.  
Essa visão inclui informações como:

- Dispositivo e componente associados
- Variável monitorada
- Período em que o desvio foi identificado
- Status atual do alarme
- Contexto operacional no momento da ocorrência

Essa página auxilia na investigação técnica e no entendimento da possível causa raiz do desvio detectado.

---

# Timeseries

A seção de **Timeseries** exibe a evolução temporal dos dados utilizados pelos modelos de predição.  
Normalmente são apresentados, no mesmo gráfico:

- Valor medido
- Valor previsto pelo modelo
- Limites ou bandas de referência

A visualização em série temporal permite comparar diretamente o comportamento real com o esperado, facilitando a interpretação dos alarmes e a validação dos resultados do modelo.
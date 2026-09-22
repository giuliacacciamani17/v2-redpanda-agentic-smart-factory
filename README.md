# Redpanda Agentic Data Plane


## Descrizione

Il progetto realizza un prototipo didattico di Agentic Data Plane
event-driven per una Smart Factory.

Una macchina simulata produce eventi telemetrici, gli eventi vengono pubblicati
sull'interfaccia Redpanda Console e successivamente elaborati da un Maintenance Agent.

L'agente valuta il rischio, sceglie un'azione e pubblica un comando, mentre un Machine Controller simulato esegue
i comandi e pubblica lo stato risultante, permettendo all'agente di osservare
gli effetti della propria decisione.

Redpanda costituisce il broker centrale e permette la comunicazione asincrona, la persistenza degli eventi, il replay, il partizionamento e la tracciabilità end-to-end.


## Obiettivi

Il progetto ha l'obiettivo di mostrare:

- il concetto di agente software;
- il ciclo percezione, decisione, azione e feedback;
- il concetto di Agentic Data Plane;
- il ruolo di Redpanda in un'architettura event-driven;
- la comunicazione asincrona tra componenti distribuiti;
- gestione automatica dei fallimenti;
- la persistenza e il replay degli eventi;
- la tracciabilità delle decisioni;
- l'utilizzo di Docker Compose e Redpanda Console.

## Architettura prevista

Il sistema sarà composto da:

- Redpanda;
- Redpanda Console;
- Machine Simulator;
- Maintenance Agent;
- Machine Controller;
- Analytics Consumer.

## Flusso principale

1. Il Machine Simulator legge l'ultimo stato disponibile della macchina e produce un blocco di eventi di telemetria coerente con tale stato.

2. Gli eventi vengono pubblicati nel topic `factory.telemetry`.

3. Redpanda conserva gli eventi e li rende disponibili al Maintenance Agent.

4. Il Maintenance Agent consuma la telemetria, aggiorna il proprio stato interno e calcola il livello di rischio.

5. L'agente sceglie un'azione e pubblica la decisione nel topic `factory.agent-decisions`.

6. Se la decisione è `NO_ACTION`, `MONITOR` oppure `STOPPED_OBSERVATION`, non viene prodotto alcun comando operativo.

7. Se la decisione è `REDUCE_SPEED`, `REQUEST_INSPECTION` oppure `EMERGENCY_STOP`, l'agente pubblica un comando nel topic `factory.commands`.

8. Il Machine Controller consuma il comando, prova a eseguirlo e pubblica l'esito nel topic `factory.command-results`.

9. Se il comando viene eseguito con successo:

   - il controller pubblica il nuovo stato effettivo della macchina nel topic `factory.machine-state`;
   - il Maintenance Agent aggiorna il proprio stato interno;
   - l'agente pubblica un feedback con stato `COMPLETED` nel topic `factory.agent-feedback`;
   - il ciclo operativo relativo al comando termina.

10. Se il comando fallisce:

    - la velocità e lo stato della macchina rimangono invariati;
    - il Maintenance Agent registra il fallimento;
    - l'agente pubblica un feedback con stato `RECOVERY_SCHEDULED`;
    - l'agente seleziona una nuova azione mediante la politica di recupero;
    - viene pubblicata una nuova decisione con `decision_type = RECOVERY`;
    - viene pubblicato un nuovo comando nel topic `factory.commands`.

11. La politica di recupero applica la seguente escalation:

    ```text
    REDUCE_SPEED fallisce
    → REQUEST_INSPECTION

    REQUEST_INSPECTION fallisce
    → EMERGENCY_STOP

    EMERGENCY_STOP fallisce
    → nuovo tentativo di EMERGENCY_STOP
    ```

12. Se viene superato il numero massimo di tentativi automatici, l'agente pubblica un feedback con stato `MANUAL_INTERVENTION_REQUIRED` e non genera ulteriori comandi.

13. Il Machine Simulator utilizza l'ultimo evento presente in `factory.machine-state` per determinare lo scenario del blocco successivo:

    ```text
    Nessuno stato precedente
    → PROGRESSIVE_DEGRADATION

    Ultima azione REDUCE_SPEED
    → RECOVERY_AFTER_SPEED_REDUCTION

    Stato INSPECTION_REQUIRED
    → INSPECTION_PENDING

    Stato STOPPED
    → STOPPED_COOLING
    ```

14. Tutti gli eventi appartenenti allo stesso ciclo decisionale mantengono lo stesso `correlation_id`, permettendo di collegare telemetria, decisioni, comandi, risultati, feedback e stato macchina.

## Tracciabilità

Gli identificatori principali sono:

```text
event_id       → telemetria
decision_id    → decisione
command_id     → comando
result_id      → risultato
feedback_id    → feedback
state_event_id → stato macchina
correlation_id → intero ciclo originato da una telemetria
```

Le decisioni di recupero mantengono lo stesso `correlation_id` del comando fallito, ma generano nuovi `decision_id` e `command_id`.


## Tecnologie

- Python
- Redpanda
- Redpanda Console
- Docker
- Docker Compose
- Git
- GitHub
- Markdown

## Avvio del progetto

### 1. Avviare Docker Desktop

Aprire Docker Desktop e attendere che il motore Docker sia pronto.

### 2. Entrare nella root del progetto

Aprire PowerShell e spostarsi nella cartella in cui è stato estratto il repository.

### 3. Verificare la configurazione Compose

```powershell
docker compose config
```

### 4. Avviare i servizi permanenti

```powershell
docker compose up -d redpanda redpanda-console maintenance-agent machine-controller
```

Il Machine Simulator non viene avviato in modo permanente. Parte soltanto quando viene richiesto un nuovo blocco di eventi.

### 5. Verificare i container

```powershell
docker compose ps
```

Devono essere attivi:

```text
redpanda-v2
redpanda-console-v2
maintenance-agent-v2
machine-controller-v2
```

`redpanda-v2` deve raggiungere lo stato `healthy`.

### 6. Creare i topic al primo avvio

```powershell
docker exec redpanda-v2 rpk topic create factory.telemetry factory.agent-decisions factory.commands factory.command-results factory.agent-feedback factory.machine-state --partitions 3
```

Se i topic esistono già, non è necessario ricrearli.

Verifica:

```powershell
docker exec redpanda-v2 rpk topic list
```

### 7. Aprire Redpanda Console

```text
http://localhost:8081
```

## Generazione di un blocco di eventi

Ogni esecuzione genera cinque eventi e poi termina.

### Da WSL o Bash

```bash
cd "/mnt/c/Users/giuli/OneDrive/Desktop/UNIMORE/anno2/semestre2/Distributed Edge Programming/v2-redpanda-agentic-smart-factory-main"
chmod +x scripts/run-simulation.sh
./scripts/run-simulation.sh
```

### Direttamente da PowerShell tramite WSL

```powershell
wsl bash -lc 'cd "/mnt/c/Users/giuli/OneDrive/Desktop/UNIMORE/anno2/semestre2/Distributed Edge Programming/v2-redpanda-agentic-smart-factory-main" && chmod +x scripts/run-simulation.sh && ./scripts/run-simulation.sh'
```

Lo script:

1. legge `.next-correlation-id`;
2. assegna cinque `correlation_id` consecutivi;
3. calcola un nuovo `RANDOM_SEED`;
4. avvia temporaneamente il Machine Simulator;
5. aggiorna il contatore soltanto dopo il completamento del blocco.

Non è necessario svuotare i topic tra due blocchi. Il blocco successivo legge l'ultimo evento di `factory.machine-state` e prosegue coerentemente dallo stato precedente.


## Configurazioni principali

| Variabile | Valore predefinito | Significato |
|---|---:|---|
| `STATE_WINDOW_SIZE` | `5` | Numero massimo di misurazioni conservate dall'agente |
| `MAX_RECOVERY_ATTEMPTS` | `3` | Numero massimo di tentativi automatici di recupero |
| `SPEED_REDUCTION_PERCENTAGE` | `20` | Percentuale di riduzione applicata da `REDUCE_SPEED` |
| `EVENT_INTERVAL_SECONDS` | `2` | Secondi di attesa tra due telemetrie dello stesso blocco |
| `STATE_READ_TIMEOUT_SECONDS` | `2` | Tempo massimo per leggere lo stato precedente |
| `CONTROLLER_MODE` | `MIXED` | Modalità di simulazione del controller |

## Documentazione

La documentazione teorica e applicativa è disponibile nella cartella `docs`:

- agenti software;
- Agentic Data Plane;
- Redpanda;
- confronto tra Redpanda e Apache Kafka.
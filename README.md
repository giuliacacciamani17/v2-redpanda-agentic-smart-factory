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

1. Il Machine Simulator legge l'ultimo stato della macchina e pubblica cinque eventi in `factory.telemetry`.

2. Il Maintenance Agent elabora la telemetria, aggiorna la memoria, calcola il rischio e pubblica la decisione in `factory.agent-decisions`.

3. Le decisioni `NO_ACTION`, `MONITOR` e `STOPPED_OBSERVATION` non producono comandi.

4. Le azioni `REDUCE_SPEED`, `REQUEST_INSPECTION` ed `EMERGENCY_STOP` vengono pubblicate in `factory.commands`.

5. Il Machine Controller esegue il comando e pubblica l'esito in `factory.command-results`.

6. Se il comando riesce:

   - l'agente pubblica un feedback `COMPLETED`;
   - il controller aggiorna `factory.machine-state`.

7. Se il comando fallisce:

   - l'agente pubblica un feedback `RECOVERY_SCHEDULED`;
   - genera una decisione `RECOVERY`;
   - pubblica un nuovo comando.

8. La politica di recupero applica questa escalation:

   ```text
   REDUCE_SPEED
   → REQUEST_INSPECTION
   → EMERGENCY_STOP
    ```

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
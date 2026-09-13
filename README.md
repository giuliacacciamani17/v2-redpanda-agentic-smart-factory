# Redpanda Agentic Smart Factory

Progetto sviluppato per l'esame di Distributed Edge Programming.

## Descrizione

Il progetto realizza un prototipo didattico di Agentic Data Plane
event-driven per una Smart Factory.

Diversi macchinari simulati producono dati telemetrici, come temperatura,
vibrazione, velocità e consumo energetico. Gli eventi vengono pubblicati
su Redpanda e successivamente elaborati da un Maintenance Agent.

L'agente mantiene uno stato per ogni macchina, valuta il rischio, sceglie
un'azione e pubblica un comando. Un Machine Controller simulato esegue
il comando e pubblica il risultato, permettendo all'agente di osservare
gli effetti della propria decisione.

## Obiettivi

Il progetto ha l'obiettivo di mostrare:

- il concetto di agente software;
- il ciclo percezione, decisione, azione e feedback;
- il concetto di Agentic Data Plane;
- il ruolo di Redpanda in un'architettura event-driven;
- la comunicazione asincrona tra componenti distribuiti;
- la persistenza e il replay degli eventi;
- la tracciabilità delle decisioni;
- l'utilizzo di Docker e Docker Compose.

## Architettura prevista

Il sistema sarà composto da:

- Redpanda;
- Redpanda Console;
- Machine Simulator;
- Maintenance Agent;
- Machine Controller;
- Analytics Consumer.

## Flusso principale

1. Il Machine Simulator produce eventi di telemetria.
2. Redpanda conserva e distribuisce gli eventi.
3. Il Maintenance Agent consuma la telemetria.
4. L'agente aggiorna il proprio stato e valuta il rischio.
5. L'agente sceglie un'azione.
6. Il comando viene pubblicato su Redpanda.
7. Il Machine Controller esegue il comando.
8. Il controller pubblica l'esito dell'azione.
9. L'agente osserva il risultato e aggiorna la propria decisione.
10. Ogni decisione viene registrata per finalità di audit.

## Tecnologie

- Python
- Redpanda
- Redpanda Console
- Docker
- Docker Compose
- Git
- GitHub
- Markdown

## Stato del progetto

Il progetto è attualmente nella fase di configurazione dell'ambiente
di sviluppo e dell'infrastruttura Redpanda.
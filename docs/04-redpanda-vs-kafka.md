# Redpanda e Apache Kafka a confronto

Redpanda e Apache Kafka sono piattaforme di **event streaming distribuito** in grado di gestire flussi di eventi in tempo reale e svolgere il ruolo di infrastruttura per la comunicazione asincrona tra applicazioni, microservizi e sistemi distribuiti.

> **Idea chiave**: Redpanda è **compatibile con il protocollo Kafka**, punta a offrire un'esperienza operativa semplificata, mantenendo il modello basato su producer, topic, partizioni, consumer e consumer group  e migliorando le prestazioni. 

---

## Cosa hanno in comune

Sia Kafka che Redpanda sono progettati per:

- gestire flussi continui di eventi
- supportare architetture event-driven;
- consentire la comunicazione asincrona tra servizi;
- garantire elevata disponibilità e tolleranza ai guasti;
- scalare orizzontalmente tramite cluster;
- supportare pattern publish/subscribe;
- memorizzare gli eventi all'interno di topic.

In entrambi i casi il principio di funzionamento è il medesimo:

```mermaid
flowchart LR
    A[Producer] --> P[Broker]
    P --> H[Consumer]
```

## Differenze principali

## Differenze principali

| Aspetto | Redpanda | Apache Kafka |
|---|---|---|
| Obiettivo operativo | Punta a ridurre la complessità di installazione e amministrazione | Offre una piattaforma ampiamente consolidata e un ecosistema molto esteso |
| Implementazione del broker | Motore nativo implementato in C++ | Broker eseguito sulla JVM |
| Gestione dei metadati | Architettura interna basata su Raft | Nelle versioni moderne utilizza KRaft |
| Strumento da terminale | Utilizza principalmente `rpk` | Utilizza gli strumenti inclusi nella distribuzione Kafka |
| Interfaccia grafica | Redpanda Console è disponibile come componente dedicato | Il progetto Apache Kafka non include una singola interfaccia grafica predefinita |
| Compatibilità | Supporta il protocollo Kafka e numerosi client Kafka | È l'implementazione originale dell'ecosistema Kafka |
| Gestione locale | Può essere avviato in modalità di sviluppo con una configurazione compatta | Richiede la configurazione dei ruoli, dei listener e della gestione KRaft |
| Ecosistema | Ecosistema in crescita e focalizzato sulla compatibilità Kafka | Ecosistema ampio, maturo e composto da numerosi strumenti e integrazioni |

Le prestazioni reali dipendono da configurazione, hardware, carico, dimensione dei messaggi, numero di partizioni, fattore di replica e requisiti di durabilità. Per dimostrare differenze prestazionali in modo rigoroso sarebbe necessario eseguire benchmark nelle stesse condizioni.


---

## Differenza nell'implementazione

Apache Kafka viene eseguito sulla **Java Virtual Machine**.

Redpanda utilizza invece un **motore nativo implementato in C++** e non richiede la JVM per eseguire il broker.

Questa differenza riguarda principalmente il **funzionamento interno delle piattaforme**. Il modello applicativo rimane simile:

```text
Producer
   ↓       
Topic
   ↓     
Consumer
```

Nel progetto, Redpanda viene avviato con:

```yaml
redpanda:
  image: redpandadata/redpanda:v26.2.1
  container_name: redpanda-v2
```

Se il progetto utilizzasse Kafka, sarebbe necessario sostituire il servizio Redpanda con uno o più servizii Kafka e configurare diversamente:

- ruoli broker e controller;
- quorum KRaft;
- listener interni ed esterni;
- inizializzazione dello storage;
- health check;
- strumenti amministrativi;
- eventuale interfaccia grafica.

---

## Differenza nella gestione dei metadati

Le versioni moderne di Apache Kafka, in sostituzione a Zookeeper, utilizzano **KRaft** per la gestione distribuita dei metadati del cluster. 

In modalità KRaft, alcuni nodi Kafka assumono il ruolo di `controller` e partecipano a un quorum. I controller mantengono un **registro condiviso dei metadati** e devono raggiungere un consenso sulle modifiche alla configurazione del cluster.

Redpanda invece utilizza una propria architettura basata su **Raft**.

Raft è un algoritmo di consenso che permette a più nodi di concordare sullo stesso stato. Un nodo opera come leader, mentre gli altri partecipanti replicano le informazioni. Una modifica viene considerata confermata quando raggiunge il consenso richiesto dal gruppo. Redpanda utilizza quindi Raft non soltanto per i **metadati**, ma anche per la **replica dei dati** applicativi contenuti nelle partizioni.



---

## Differenza nell'interfaccia grafica

Nel progetto viene utilizzata **Redpanda Console**, accessibile tramite:

```text
http://localhost:8081
```

La Console permette di osservare:

- topic;
- messaggi JSON;
- chiavi;
- partizioni;
- offset;
- consumer group;
- lag;
- decisioni dell'agente;
-comandi iniziali e comandi di recupero;
- risultati `SUCCESS` e `FAILED`;
- feedback di vario genere;
- `correlation_id`.

**Apache Kafka non include una singola interfaccia grafica** predefinita nel progetto Apache. Per ottenere una visualizzazione simile è necessario scegliere e configurare uno strumento compatibile.

---

## Che cosa hanno in comune Redpanda e Kafka

Redpanda e Kafka condividono il modello fondamentale dell'event streaming.

**1. Producer**: crea e pubblica eventi.


**2. Broker**: riceve, conserva e distribuisce gli eventi.

**3. Consumer**: legge ed elabora gli eventi.


**4. Topic**: entrambe le piattaforme organizzano gli eventi in topic.

**5. Partizioni**: Redpanda e Kafka possono dividere ogni topic in più partizioni, queste permettono di:

- distribuire i record;
- mantenere l'ordine all'interno di una partizione;
- aumentare il parallelismo;
- dividere il lavoro tra più consumer.

**6. Chiavi**: entrambe le piattaforme permettono di associare una chiave ai record. Gli eventi della stessa macchina vengono così indirizzati coerentemente verso la stessa partizione del relativo topic.

**7. Offeset**: Redpanda e Kafka assegnano a ogni record un offset all'interno della partizione, rappresentando la posizione del record nella partizione.

**8. Consumer Group**: entrambe le piattaforme supportano i consumer group, che consentono alle istanze della stessa applicazione di coordinarsi e dividersi le partizioni.
---
# Quando utilizzare Kafka

Kafka rappresenta spesso la scelta migliore quando:

- l'organizzazione possiede già un ecosistema Kafka consolidato;
- sono presenti cluster di grandi dimensioni;
- è richiesta una piattaforma ampiamente collaudata;
- si opera in contesti enterprise molto complessi;
- sono necessari strumenti altamente specializzati dell'ecosistema Kafka;
- sono già disponibili competenze operative su Kafka e KRaft.

---
# Quando utilizzare Redpanda

Redpanda rappresenta una scelta molto interessante quando:

- si desidera ridurre la complessità operativa;
- si vuole una soluzione più semplice da gestire;
- si sta sviluppando una nuova architettura cloud-native;
- si necessita di elevate prestazioni con infrastruttura ridotta;
- si realizzano sistemi basati su eventi, AI Agent o architetture agentiche;
- si desidera una compatibilità con Kafka senza adottarne tutta la complessità.

---

## Compatibilità con il client Python

Il progetto utilizza:

```python
from confluent_kafka import Consumer, Producer
```

La libreria `confluent-kafka` comunica attraverso il protocollo Kafka e può essere utilizzata con Redpanda.

La configurazione del consumer usa proprietà compatibili con Kafka:

```python
configuration = {
    "bootstrap.servers": KAFKA_BROKER,
    "group.id": CONSUMER_GROUP,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
}
```

Anche la pubblicazione segue il modello Kafka:

```python
producer.produce(
    topic=topic,
    key=machine_id.encode("utf-8"),
    value=json.dumps(event).encode("utf-8"),
    callback=delivery_report,
)
```

Questa compatibilità favorisce la **portabilità** del codice applicativo.

Redpanda e Kafka non sono identici, ma gran parte del codice Python potrebbe essere riutilizzata passando da una piattaforma all'altra.  Le differenze più rilevanti riguarderebbero la configurazione e la gestione dell'infrastruttura.

---

## Vantaggi di Redpanda nel progetto

Redpanda è stato scelto perché permette di realizzare un ambiente di sviluppo locale **semplice** e soprattutto **chiaramente osservabile**.

### 1. Avvio attraverso Docker Compose

Il file `compose.yaml` contiene il broker, la Console, il simulatore, il Maintenance Agent e il Machine Controller.

Questa configurazione permette di avviare l'intera architettura con pochi comandi.

### 2. Compatibilità con `confluent-kafka`

Redpanda permette di utilizzare il client Python scelto per il progetto:

```text
confluent-kafka
```

Non è stato quindi necessario utilizzare una libreria specifica e proprietaria per produrre o consumare eventi.


### 3. Disponibilità di Redpanda Console

Redpanda Console permette di vedere graficamente i messaggi presenti nei topic.

Questa funzione è particolarmente utile in un progetto accademico perché permette di seguire facilmente il percorso di ogni evento.

### 4. Osservazione del ciclo agentico

Attraverso Redpanda Console è possibile seguire lo stesso `correlation_id` nei diversi topic.


Questo rende più semplice dimostrare il funzionamento del Maintenance Agent.




---

## Che cosa cambierebbe usando Kafka

La logica principale del progetto potrebbe rimanere quasi invariata.

Cambierebbero principalmente gli aspetti infrastrutturali:

1. immagine Docker del broker;
2. configurazione KRaft;
3. listener e porte;
4. inizializzazione dello storage;
5. health check;
6. strumenti amministrativi;
7. interfaccia grafica;
8. procedure di avvio e manutenzione.

Il broker configurato nei servizi potrebbe diventare:

```yaml
KAFKA_BROKER: kafka:9092
```

Potrebbero restare uguali:

- Machine Simulator;
- Maintenance Agent;
- Risk Engine;
- policy decisionale;
- Machine Controller;
- eventi JSON;
- nomi dei topic;
- `machine_id`;
- `correlation_id`;
- consumer group;
- gestione degli offset;
- lettura dello stato macchina;
- decisioni `INITIAL` e `RECOVERY`;
- comandi con `current_speed` e `target_speed`.


Il client Python potrebbe continuare a essere:

```python
from confluent_kafka import Consumer, Producer
```

Questo dimostra che la logica della Smart Factory è separata dalla tecnologia specifica utilizzata come broker.


---

## Riferimenti

- Redpanda Documentation, How Redpanda Works: <https://docs.redpanda.com/streaming/current/get-started/architecture/>
- Redpanda Documentation, Kafka Compatibility: <https://docs.redpanda.com/streaming/current/develop/kafka-clients/>
- Redpanda Documentation, rpk: <https://docs.redpanda.com/streaming/current/reference/rpk/>
- Apache Kafka official website: <https://kafka.apache.org/>
- Apache Kafka Documentation, KRaft: <https://kafka.apache.org/documentation/#kraft>
# Testing documentation

([*Le français est disponible au bas de la page*](#documentation-des-tests))

## Table of Contents

- [Test Case: Populate model selection component with pipelines information](#test-case-populate-model-selection-component-with-pipelines-information)
- [Test Case: Inference Request](#test-case-inference-request)
- [Documentation des tests](#documentation-des-tests)
- [Cas de Test : Remplir le composant de sélection de modèle avec les informations des pipelines](#cas-de-test--remplir-le-composant-de-sélection-de-modèle-avec-les-informations-des-pipelines)
- [Cas de test : requête d'inférence](#cas-de-test--requête-dinférence)

To start the automatic test, you can use the following command:

```bash
python -m unittest discover -s tests
```

You also have the option to run automatic tests in run_test.py or manually test
the functionality with the frontend. [See frontend testing
documentation](https://github.com/ai-cfia/nachet-frontend/blob/main/TESTING.md)

To perform the following test, you will need the Nachet's frontend repository.
It can be found at: [Nachet Frontend GitHub
Repository](https://github.com/ai-cfia/nachet-frontend).

You will also need the list of the available pipelines. The list can be found
[here](https://github.com/ai-cfia/nachet-backend/blob/51-implementing-2-models/docs/nachet-inference-documentation.md#available-version-of-the-json-file).

## Test Case: Populate model selection component with pipelines information

**Objective**: Verify that the model selection component gets populated with the
pipeline information.

### Preconditions

- [ ] Nachet backend is set up and running. Use the command `hypercorn -b :8080
  app:app` to start the quart server.
- [ ] The environment variables are all set.
- [ ] :exclamation: The frontend is not running yet

### Test Steps

1. Start the frontend application
1. Click on the model selection button
1. Validate that the current pipeline is selectable.

### Expected Results

- [ ] If a problem occurs while retrieving the data, an error should prevent the
  server from starting.
- [ ] If a problem occurs while retrieving the data, but no error was raised,
  the model selection component should be empty.
- [ ] If everything went correctly while retrieving the data, the model
  selection component should display the pipeline metadata.

### Actual Results

- [ ] Describe the actual outcome of the test

### Pass/Fail Criteria

- [ ] Pass if the metadata from the available pipeline is displayed.
- [ ] Fail if the metadata from the available pipeline is not displayed and no
  error was raised.

## Test Case: Inference Request

### Objective: Verify that the inference request endpoint `/inf` behaves as expected

### Preconditions_

- [ ] Nachet backend is set up and running. Use the command `hypercorn -b :8080
  app:app` to start the quart server.
- [ ] The environment variables are all set.
- [ ] The frontend is running.
- [ ] Start the frontend application
- [ ] Click on the model selection button
- [ ] Validate that the current pipeline is selectable

### Test Steps_

1. Upload a seed image
1. Select the first model (pipeline)
1. Click on the classify button
1. Wait until the results populate on the canvas
1. Repeat the process for every model (pipeline)

|:boom: Warning| |----------------------| |Displaying results from two different
models will overlap and become unreadable.|

### Expected Results_

- [ ] The data populates both the canvas and the results components with the
  prediction data from the model (pipeline).
- [ ] An alert with an error from port 3000 or 8080 is displayed.

### Actual Results_

- [ ] Describe the actual outcome of the test

### Pass/Fail Criteria_

- [ ] Pass if the data is populated on both the canvas and the results component
  with the prediction of the model (pipeline).
- [ ] Fail if an alert is displayed with an error message.
- [ ] Fail if the data is not populated on the canvas and the results component
- [ ] Fail if the inference is stuck in an infinite loop

---

## Documentation des tests

Pour lancer les tests automatiques, vous pouvez utiliser la commande suivante :

```bash
python -m unittest discover -s tests
```

Vous avez également la possibilité d'exécuter les tests automatiques dans
`run_test.py` ou de tester manuellement les fonctionnalités avec le frontend.
[Voir la documentation des tests du
frontend](https://github.com/ai-cfia/nachet-frontend/blob/main/TESTING.md).

Pour effectuer les tests suivants, vous aurez besoin du dépôt frontend de
l'application Nachet Interactive. Le frontend se trouve ici : [Dépôt GitHub du
frontend Nachet](https://github.com/ai-cfia/nachet-frontend).

Vous aurez également besoin de la liste des pipelines disponibles. La liste se
trouve
[ici](https://github.com/ai-cfia/nachet-backend/blob/51-implementing-2-models/docs/nachet-inference-documentation.md#available-version-of-the-json-file).

## Cas de Test : Remplir le composant de sélection de modèle avec les informations des pipelines

### Objectif : Vérifier que le composant de sélection de modèle est correctement rempli avec les informations des pipelines

### Prérequis

- [ ] Le backend Nachet est configuré et en cours d'exécution. Utilisez la
  commande `hypercorn -b :8080 app:app` pour démarrer le serveur Quart.
- [ ] Les variables d'environnement sont correctement configurées.
- [ ] :exclamation: Le frontend n'est pas encore démarré.

### Étapes de test

1. Démarrez l'application frontend.
2. Cliquez sur le bouton de sélection de modèles.
3. Validez que le pipeline actuel est sélectionnable.

### Résultats attendus

- [ ] En cas de problème lors de la récupération des données, une erreur doit
  empêcher le serveur de démarrer.
- [ ] En cas de problème sans erreur levée, le composant de sélection de modèles
  doit rester vide.
- [ ] Si tout fonctionne correctement, le composant de sélection de modèles doit
  afficher les métadonnées des pipelines.

### Résultats réels

- [ ] Décrivez les résultats réels du test.

### Critères de Succès/Échec

- [ ] Succès si les métadonnées des pipelines disponibles sont affichées.
- [ ] Échec si les métadonnées ne sont pas affichées et aucune erreur n'a été
  levée.

## Cas de test : requête d'inférence

### Objectif** : Vérifier que le point de terminaison `/inf` de requête d'inférence se comporte comme prévu

### Prérequis_

- [ ] Le backend Nachet est configuré et en cours d'exécution. Utilisez la
  commande `hypercorn -b :8080 app:app` pour démarrer le serveur Quart.
- [ ] Les variables d'environnement sont correctement configurées.
- [ ] Le frontend est démarré.
- [ ] Cliquez sur le bouton de sélection de modèles.
- [ ] Validez que le pipeline actuel est sélectionnable.

### Étapes de test_

1. Téléversez une image de graine.
2. Sélectionnez le premier modèle (pipeline).
3. Cliquez sur le bouton de classification.
4. Attendez que les résultats soient affichés sur le canevas.
5. Répétez le processus pour chaque modèle (pipeline).

| :boom: Avertissement |  
|----------------------|  
| Les résultats affichés de deux modèles différents se superposent et deviennent illisibles. |

### Résultats attendus_

- [ ] Les données peuplent à la fois le canevas et les composants de résultats
  avec les prédictions du modèle (pipeline).
- [ ] Une alerte avec une erreur des ports 3000 ou 8080 est affichée.

### Résultats réels_

- [ ] Décrivez les résultats réels du test.

### Critères de succès/échec

- [ ] Succès si les données peuplent le canevas et les composants de résultats
  avec les prédictions du modèle (pipeline).
- [ ] Échec si une alerte est affichée avec un message d'erreur.
- [ ] Échec si les données ne peuplent pas le canevas et les composants de
  résultats.
- [ ] Échec si la requête d'inférence reste bloquée dans une boucle infinie.

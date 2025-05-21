# Nachet Interactive Models

([*Le français est disponible au bas de la page*](#modèles-nachet-interactive))

## Table of Contents

- [Executive Summary](#executive-summary)
- [Task](#task)
- [List of Models](#list-of-models)
  - [Request Inference Function](#request-inference-function)
  - [Return Value of Models](#return-value-of-models)
  - [Why topN](#why-topn)
  - [Bounding Boxes](#bounding-boxes)
- [Different Ways of Calling Models](#different-ways-of-calling-models)
  - [Header](#header)
  - [Body](#body)
- [Error from Models](#error-from-models)
- [Pipeline and Model Data](#pipeline-and-model-data)
  - [Key Description](#key-description)
    - [File Specific Keys](#file-specific-keys)
    - [Pipeline Specific Keys](#pipeline-specific-keys)
    - [Model Specific Keys](#model-specific-keys)
  - [JSON Representation and Example](#json-representation-and-example)

## Executive Summary

Nachet Interactive uses various models to detect seeds. Documentation is
essential to keep track of their features. The models can perform different
tasks, including Image Classification, Image Segmentation, or Object Detection.

## Task

Nachet Interactive's models perfom the following tasks:

|Task|Action|Input/Output|
|:--|:--|:-----|
|[Classification](https://huggingface.co/tasks/image-classification) | This task involves assigning a single label or class to each image the model receives. | The input for the classification models is an image, and the output is a prediction of the class it belongs to. |
|[Object Detection](https://huggingface.co/tasks/object-detection) | Identify and locate an object belonging to a specific class within an image. |The object detection models take an image as an input and output the image with a label and a box around the detected object. |
|[Segmentation](https://huggingface.co/tasks/image-segmentation) | Segmentation is the task of dividing images into different parts, where each pixel in the image is mapped to an object. It includes instance segmentation, panoptic segmentation, and semantic segmentation.| The segmentation models take an image as input and return an image divided into objects. |

> As of today (2024-02-22), none of our models use segmentation. To know more
> about each task, click on the task to follow the link to their hugging face
> page. To know more about AI tasks in general: [Hugging Face
> Tasks](https://huggingface.co/tasks)

## List of Models

|Model|Full name|Task|API Call Function|Inference Function|Active|Accuracy|
|--|--|:--:|:--:|:--:|:--:|:--:|
|Nachet-6seeds | m-14of15seeds-6seedsmag | Object Detection | nachet_6seeds | None | Yes | - |
|Seed-detector | seed-detector-1 |  Object Detection | seed_detector | process_image_slicing | Yes | - |
|Swin | swinv1-base-dataaugv2-1 | Classification | swin | process_swin_result | Yes | - |

### Request Inference Function

The request inference functions request a prediction from the specified model
(such as Swin, Nachet-6seeds, etc.). If needed, the function will process the
data to be readable by the next model in the pipeline. For instance, the
Seed-detector only returns "seed" as a label, and its inference needs to be
processed and passed to the next model which assigns the correct label to the
seeds.

## Return Value of Models

```json
{
    "filename": "tmp/tmp_file_name",
    "boxes": [
        {"box": {
                "topX": 0.0,
                "topY": 0.0,
                "bottomX": 0.0,
                "bottomY": 0.0
            },
        "label": "top_label_name",
        "score": 0.912,
        "color": "#ff0",
        "topN": [
            {
                "score": 0.912,
                "label": "top_label_name",
            },
            {
                "score": 0.053,
                "label": "seed_name",
            },
            {
                "score": 0.0029,
                "label": "seed_name",
            },
            {
                "score": 0.005,
                "label": "seed_name",
            },
            {
                "score": 0.001,
                "label": "seed_name",
            }
        ],
        "overlapping": false,
        "overlappingIndices": 0
        },
    ],
    "labelOccurrence": {
        "seed_name": 1,
    },
    "totalBoxes": 1
}
```

### Why topN

We decided to name the top results property `topN` because this value can return
n predictions. Usually in AI, the top 5 results are used to measure the accuracy
of a model. If the correct result is the top 5, then the prediction is
considered true.

This is helpful in situations where the user needs to focus on multiple results
simultaneously.

 > "Top N accuracy — Top N accuracy is when you measure how often your predicted
 > class falls in the top N values of your softmax distribution." [Nagda, R.
 (2019-11-08) *Evaluating models using the Top N accuracy metrics*.
 Medium](https://medium.com/nanonets/evaluating-models-using-the-top-n-accuracy-metrics-c0355b36f91b)

### Bounding Boxes

The `box` key stores the value for a specific box around a seed. This helps the
frontend draw a red rectangle around every seed on the image.

![image](https://github.com/ai-cfia/nachet-backend/assets/96267006/469add8d-f40a-483f-b090-0ebcb7a8396b)

## Different Ways of Calling Models

### Header

The endpoint can host multiple models, so specifying the model name in the
header is necessary to avoid errors.

```python
# Header for every model should be:
headers = {
    'Content-Type': 'application/json',
    'Authorization': ('Bearer ' + endpoint_api_key),
    'azureml-model-deployment': model_name
}
```

### Body

The body structure is dependant on the model tasks. A classification model can
only classify one seed in an image, whereas an object detection model can detect
if the image contains one or multiple seeds. It remains to be determined whether
a segmentation model requires a different body structure. [See task](#task)

```python
# Object Detection model
# Example: Nachet-6seeds and seed-detector
body = {
    'input_data': {
        'columns': ['image'],
        'index': [0],
        'data': [image_bytes],
    }
}

# Classification model
# Example: Swin
body = b64encode(image)
```

## Error from Models

A list of common errors models return to the backend.

> To access the error from the model, go to the model endpoint in Azure and look
> for the logs : CFIA/ACIA/workspace/endpoint/model/logs

|Error|Model|Reason|Message|
|--|--|--|--|
|ValueError| Swin |Incorrect image source|Must be a valid url starting with `http://` or `https://`, a valid path to an image file, or a base64 encoded string|

## Pipeline and Model Data

In order to dynamically build the pipeline in the backend from the model, the
following data structure was designed. For now, the pipelines will have two keys
for their names (`model_name`, `piepline_name`) to support the frontend code
until it is changed to get the name of the pipeline with the correct key.

```yaml
version:
date:
pipelines:
  - models:
    model_name:
    pipeline_name:
    created_by:
    creation_date:
    version:
    description:
    job_name:
    dataset_description:
    accuracy:
    default:

models:
  - task:
    endpoint:
    api_key:
    content_type:
    deployment_platform:
    endpoint_name:
    model_name:
    created_by:
    creation_date:
    version:
    description:
    job_name:
    dataset_description:
    accuracy:
```

### Key Description

#### File Specific Keys

|Key|Description|Expected Value Format|
|--|--|--|
|version|The version of the file|0.0.0|
|date|The date the file was upload|202x-mm-dd|
|pipelines|A list of available pipeline||
|models|A list of available model||

#### Pipeline Specific Keys

|Key|Description|Expected Value Format|
|--|--|--|
|models|A list of the model name used by the pipeline in order|["that_model_name", "other_model_name"]|
|pipeline_name|The pipeline name|"First Pipeline"|
|created_by|The creator of the pipeline|"Avery GoodDataScientist"|
|version|The version of the pipeline|1|
|description|The pipeline's description|"Pipeline Description"|
|job_name|The pipeline job name|"Job Name"|
|dataset_description|A brief description of the dataset|"Dataset Description"|
|Accuracy|The prediction accuracy of the pipeline|0.8302|
|default|Determine if the pipeline is the default one|true or false|

#### Model Specific Keys

|Key|Description|Expected Value Format|
|--|--|--|
|tasks|The model task|"object-detection", "classification" or "segmentation"|
|endpoint|The model endpoint|["https://that-model.inference.ml.com/score"](#model-specific-keys)|
|api_key|Secret key to access the API|"SeCRetKeys"|
|content_type|The content type the model can process|"application/json"|
|deployment_platform|The platform where the model is hosted|"azure"|
|endpoint_name|The model endpoint name|"that-model-endpoint"|
|model_name|The name of the model|"that_model_name"|
|created_by|The creator of the model|"Avery GoodDataScientist"|
|creation_date|The creation date of the model|"2024-03-18"|
|version|The version of the model|1|
|description|The description of the model|"Model Description"|
|job_name|The job name of the model|"Job Name"|
|dataset_description|A brief description of the dataset|"Dataset Description"|
|Accuracy|The prediction accuracy of the model|0.9205|

#### JSON Representation and Example

This how the file is represented in the datastore.

```json
{
    "version": "0.1.0",
    "date": "2024-02-26",
    "pipelines":
    [
        {
            "models": ["that_model_name", "other_model_name"],
            "pipeline_name": "First Pipeline",
            "created_by": "Avery GoodDataScientist",
            "creation_date": "2024-01-01",
            "version": 1,
            "description": "Pipeline Description",
            "job_name": "Job Name",
            "dataset_description": "Dataset Description",
            "Accuracy": 0.8302,
            "default": true
        },
        {
            "models": ["that_model_name"],
            "pipeline_name": "Second Pipeline",
            "created_by": "Avery GoodDataScientist",
            "creation_date": "2024-01-02",
            "version": 2,
            "description": "Pipeline Description",
            "job_name": "Job Name",
            "dataset_description": "Dataset Description",
            "Accuracy": 0.7989,
            "default": true
        },
    ],
    "models":
    [
        {
            "task": "classification",
            "endpoint": "https://that-model.inference.ml.com/score",
            "api_key": "SeCRetKeys",
            "content_type": "application/json",
            "deployment_platform": "azure",
            "endpoint_name": "that-model-endpoint",
            "model_name": "that_model_name",
            "created_by": "Avery GoodDataScientist",
            "creation_date": "2023-12-02",
            "version": 5,
            "description": "Model Description",
            "job_name": "Job Name",
            "dataset_description": "Dataset Description",
            "Accuracy": 0.6908
        },
        {
            "task": "object-detection",
            "endpoint": "https://other-model.inference.ml.com/score",
            "api_key": "SeCRetKeys",
            "content_type": "application/json",
            "deployment_platform": "aws",
            "endpoint_name": "other-model-endpoint",
            "model_name": "other_model_name",
            "created_by": "Avery GoodDataScientist",
            "creation_date": "2023-11-25",
            "version": 3,
            "description": "Model Description",
            "job_name": "Job Name",
            "dataset_description": "Dataset Description",
            "Accuracy": 0.9205
        },
    ]
}
```

---

## Modèles Nachet Interactive

## Table des matières

- [Résumé](#résumé)
- [Tâches](#tâches)
- [Liste des modèles](#liste-des-modèles)
  - [Fonctions de requête d'inférence](#fonctions-de-requête-dinférence)
  - [Valeur de retour des modèles](#valeur-de-retour-des-modèles)
  - [Pourquoi topN](#pourquoi-topn)
  - [Cadres de contour](#cadres-de-contour)
- [Différentes façons d'appeler les modèles](#différentes-façons-dappeler-les-modèles)
  - [En-tête (Header)](#en-tête-header)
  - [Corps (Body)](#corps-body)
- [Erreurs des modèles](#erreurs-des-modèles)
- [Pipeline et données des modèles](#pipeline-et-données-des-modèles)
  - [Description des clés](#description-des-clés)
    - [Clés spécifiques au fichier](#clés-spécifiques-au-fichier)
    - [Clés spécifiques au pipeline](#clés-spécifiques-au-pipeline)
    - [Clés spécifiques au modèle](#clés-spécifiques-au-modèle)
  - [Représentation JSON et exemple](#représentation-json-et-exemple)

## Résumé

Nachet Interactive utilise divers modèles pour détecter les graines. Une
documentation est essentielle pour suivre leurs fonctionnalités. Les modèles
peuvent réaliser différentes tâches, notamment la classification d'images, la
segmentation d'images et la détection d'objets.

## Tâches

Les modèles de Nachet Interactive réalisent les tâches suivantes :

| Tâche | Action | Entrée/Sortie |
|:--|:--|:-----|
| [Classification](https://huggingface.co/tasks/image-classification) | Cette tâche consiste à attribuer une seule étiquette ou classe à chaque image que le modèle reçoit. | L'entrée pour les modèles de classification est une image, et la sortie est une prédiction de la classe à laquelle elle appartient. |
| [Détection d'objets](https://huggingface.co/tasks/object-detection) | Identifier et localiser un objet appartenant à une classe spécifique dans une image. | Les modèles de détection d'objets prennent une image en entrée et produisent une image avec une étiquette et un cadre autour de l'objet détecté. |
| [Segmentation](https://huggingface.co/tasks/image-segmentation) | La segmentation consiste à diviser les images en différentes parties, où chaque pixel de l'image est associé à un objet. Cela inclut la segmentation d'instances, la segmentation panoptique et la segmentation sémantique. | Les modèles de segmentation prennent une image en entrée et renvoient une image divisée en objets. |

> À ce jour (22/02/2024), aucun modèle n'utilise la segmentation. Pour en savoir
> plus sur chaque tâche, cliquez sur le lien correspondant à leur page Hugging
> Face. Pour en savoir plus sur les tâches d'IA en général : [Tâches Hugging
> Face](https://huggingface.co/tasks).

## Liste des modèles

| Modèle | Nom complet | Tâche | Fonction d'appel API | Fonction d'inférence | Actif | Précision |
|--|--|:--:|:--:|:--:|:--:|:--:|
| Nachet-6seeds | m-14of15seeds-6seedsmag | Détection d'objets | nachet_6seeds | Aucun | Oui | - |
| Seed-detector | seed-detector-1 | Détection d'objets | seed_detector | process_image_slicing | Oui | - |
| Swin | swinv1-base-dataaugv2-1 | Classification | swin | process_swin_result | Oui | - |

### Fonctions de requête d'inférence

Les fonctions de requête d'inférence sont utilisées pour demander une prédiction
au modèle spécifié (par exemple, Swin, Nachet-6seeds, etc.). Si nécessaire, ces
fonctions traitent également les données afin qu'elles soient compatibles avec
le prochain modèle dans la chaîne. Par exemple, Seed-detector ne retourne que
"seed" comme étiquette, et ses inférences doivent être traitées et transmises au
modèle suivant qui attribue les étiquettes correctes aux graines.

## Valeur de retour des modèles

```json
{
    "filename": "tmp/tmp_file_name",
    "boxes": [
        {"box": {
                "topX": 0.0,
                "topY": 0.0,
                "bottomX": 0.0,
                "bottomY": 0.0
            },
        "label": "top_label_name",
        "score": 0.912,
        "color": "#ff0",
        "topN": [
            {
                "score": 0.912,
                "label": "top_label_name"
            },
            {
                "score": 0.053,
                "label": "seed_name"
            },
            {
                "score": 0.0029,
                "label": "seed_name"
            },
            {
                "score": 0.005,
                "label": "seed_name"
            },
            {
                "score": 0.001,
                "label": "seed_name"
            }
        ],
        "overlapping": false,
        "overlappingIndices": 0
        }
    ],
    "labelOccurrence": {
        "seed_name": 1
    },
    "totalBoxes": 1
}
```

### Pourquoi topN

Nous avons décidé de nommer la propriété des meilleurs résultats "top N" parce
que cette valeur peut retourner *n* prédictions. Habituellement, en IA, les 5
meilleurs résultats sont utilisés pour mesurer la précision d'un modèle. Si le
résultat correct se retrouve dans le top 5, la prédiction est alors considérée
comme correcte.

Cela est utile dans les cas où l'utilisateur porte son attention sur plusieurs
résultats.

> "Top N accuracy — La précision Top N est une mesure indiquant à quelle
> fréquence la classe prédite se trouve parmi les N meilleures valeurs de votre
> distribution softmax."  
> [Nagda, R. (2019-11-08) *Evaluating models using the Top N accuracy metrics*.
> Medium](https://medium.com/nanonets/evaluating-models-using-the-top-n-accuracy-metrics-c0355b36f91b)

### Cadres de contour

La clé `box` stocke les valeurs pour un cadre de contour spécifique autour d'une
graine. Cela permet au frontend de dessiner un rectangle rouge autour de chaque
graine sur l'image.

![image](https://github.com/ai-cfia/nachet-backend/assets/96267006/469add8d-f40a-483f-b090-0ebcb7a8396b)

## Différentes façons d'appeler les modèles

### En-tête (Header)

Le point de terminaison peut héberger plusieurs modèles, il est donc nécessaire
de spécifier le nom du modèle dans l'en-tête pour éviter les erreurs.

```python
# L'en-tête pour chaque modèle doit être :
headers = {
    'Content-Type': 'application/json',
    'Authorization': ('Bearer ' + endpoint_api_key),
    'azureml-model-deployment': model_name
}
```

### Corps (Body)

La structure du corps de la requête varie en fonction des tâches du modèle. Un
modèle de classification peut uniquement classifier une graine dans une image,
tandis qu'un modèle de détection d'objets peut détecter si l'image contient une
ou plusieurs graines. Il reste à déterminer si un modèle de segmentation
nécessite une structure de corps différente. [Voir tâches](#tâches)

```python
# Modèle de détection d'objets
# Exemple : Nachet-6seeds et seed-detector
body = {
    'input_data': {
        'columns': ['image'],
        'index': [0],
        'data': [image_bytes],
    }
}

# Modèle de classification
# Exemple : Swin
body = b64encode(image)
```

## Erreurs des modèles

Une liste des erreurs courantes renvoyées par les modèles au backend.

> Pour accéder aux erreurs des modèles, allez sur l’endpoint du modèle dans
> Azure et consultez les journaux : CFIA/ACIA/workspace/endpoint/model/logs

|Erreur|Modèle|Raison|Message|
|--|--|--|--|
|ValueError| Swin |Source de l'image incorrecte|Doit être une URL valide commençant par `http://` ou `https://`, un chemin valide vers un fichier image ou une chaîne encodée en base64.|

## Pipeline et données des modèles

Afin de construire dynamiquement le pipeline dans le backend à partir du modèle,
la structure de données suivante a été conçue. Pour le moment, les pipelines
auront deux clés pour leurs noms (`model_name`, `pipeline_name`) pour prendre en
charge le code frontend jusqu'à ce qu'il soit modifié pour obtenir le nom du
pipeline avec la clé correcte.

```yaml
version:
date:
pipelines:
  - models:
    model_name:
    pipeline_name:
    created_by:
    creation_date:
    version:
    description:
    job_name:
    dataset_description:
    accuracy:
    default:

models:
  - task:
    endpoint:
    api_key:
    content_type:
    deployment_platform:
    endpoint_name:
    model_name:
    created_by:
    creation_date:
    version:
    description:
    job_name:
    dataset_description:
    accuracy:
```

### Description des clés

#### Clés spécifiques au fichier

|Clé|Description|Format Attendu|
|--|--|--|
|version|La version du fichier|0.0.0|
|date|La date de téléchargement du fichier|202x-mm-jj|
|pipelines|Une liste des pipelines disponibles||
|models|Une liste des modèles disponibles||

#### Clés spécifiques au pipeline

|Clé|Description|Format Attendu|
|--|--|--|
|models|Une liste des noms de modèles utilisés par le pipeline dans l'ordre|["that_model_name", "other_model_name"]|
|pipeline_name|Le nom du pipeline|"Premier Pipeline"|
|created_by|Le créateur du pipeline|"Avery GoodDataScientist"|
|version|La version du pipeline|1|
|description|La description du pipeline|"Description du Pipeline"|
|job_name|Le nom de la tâche associée au pipeline|"Nom de la Tâche"|
|dataset_description|Une brève description du dataset|"Description du Dataset"|
|Accuracy|La précision des prédictions du pipeline|0.8302|
|default|Détermine si le pipeline est celui par défaut|true ou false|

#### Clés spécifiques au modèle

|Clé|Description|Format Attendu|
|--|--|--|
|tasks|La tâche effectuée par le modèle|"object-detection", "classification" ou "segmentation"|
|endpoint|L'endpoint du modèle|["https://that-model.inference.ml.com/score"](#model-specific-keys)|
|api_key|Clé secrète pour accéder à l'API|"SeCRetKeys"|
|content_type|Le type de contenu que le modèle peut traiter|"application/json"|
|deployment_platform|La plateforme d'hébergement du modèle|"azure"|
|endpoint_name|Le nom de l'endpoint du modèle|"that-model-endpoint"|
|model_name|Le nom du modèle|"that_model_name"|
|created_by|Le créateur du modèle|"Avery GoodDataScientist"|
|creation_date|La date de création du modèle|"2024-03-18"|
|version|La version du modèle|1|
|description|La description du modèle|"Description du Modèle"|
|job_name|Le nom de la tâche associée au modèle|"Nom de la Tâche"|
|dataset_description|Une brève description du dataset|"Description du Dataset"|
|Accuracy|La précision des prédictions du modèle|0.9205|

#### Représentation JSON et exemple

Voici comment le fichier sera représenté dans le datastore.

```json
{
    "version": "0.1.0",
    "date": "2024-02-26",
    "pipelines":
    [
        {
            "models": ["that_model_name", "other_model_name"],
            "pipeline_name": "Premier Pipeline",
            "created_by": "Avery GoodDataScientist",
            "creation_date": "2024-01-01",
            "version": 1,
            "description": "Description du Pipeline",
            "job_name": "Nom de la Tâche",
            "dataset_description": "Description du Dataset",
            "Accuracy": 0.8302,
            "default": true
        },
        {
            "models": ["that_model_name"],
            "pipeline_name": "Deuxième Pipeline",
            "created_by": "Avery GoodDataScientist",
            "creation_date": "2024-01-02",
            "version": 2,
            "description": "Description du Pipeline",
            "job_name": "Nom de la Tâche",
            "dataset_description": "Description du Dataset",
            "Accuracy": 0.7989,
            "default": true
        }
    ],
    "models":
    [
        {
            "task": "classification",
            "endpoint": "https://that-model.inference.ml.com/score",
            "api_key": "SeCRetKeys",
            "content_type": "application/json",
            "deployment_platform": "azure",
            "endpoint_name": "that-model-endpoint",
            "model_name": "that_model_name",
            "created_by": "Avery GoodDataScientist",
            "creation_date": "2023-12-02",
            "version": 5,
            "description": "Description du Modèle",
            "job_name": "Nom de la Tâche",
            "dataset_description": "Description du Dataset",
            "Accuracy": 0.6908
        },
        {
            "task": "object-detection",
            "endpoint": "https://other-model.inference.ml.com/score",
            "api_key": "SeCRetKeys",
            "content_type": "application/json",
            "deployment_platform": "aws",
            "endpoint_name": "other-model-endpoint",
            "model_name": "other_model_name",
            "created_by": "Avery GoodDataScientist",
            "creation_date": "2023-11-25",
            "version": 3,
            "description": "Description du Modèle",
            "job_name": "Nom de la Tâche",
            "dataset_description": "Description du Dataset",
            "Accuracy": 0.9205
        }
    ]
}
```

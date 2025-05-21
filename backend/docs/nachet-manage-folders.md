# Manage Folders

([*Le français est disponible au bas de la page*](#gérer-les-dossiers))

## Table of Contents

- [Executive Summary](#executive-summary)
- [Prerequisites](#prerequisites)
- [Sequence Diagram](#sequence-diagram)
  - [Delete Use Case](#delete-use-case)
- [API Routes](#api-routes)
  - [/create-dir](#create-dir)
  - [/get-directories](#get-directories)
  - [/get-picture](#get-picture)
  - [/delete-request](#delete-request)
  - [/delete-permanently](#delete-permanently)
  - [/delete-with-archive](#delete-with-archive)

## Executive Summary

A user is able to have a preview of his blob storage container in the Nachet
application. He can have many folders in his container and pictures in it. Since
we have the database, those folders are related to the picture_set table and
each picture is also saved in the database. Here is its schema:

``` mermaid
---
title: Extract from Nachet DB Structure 
---
erDiagram
  picture_set{
    uuid id PK
    json picture_set
    uuid owner_id FK
    timestamp upload_date
  }
  picture{
    uuid id PK
    json picture
    uuid picture_set_id FK
    uuid parent FK
    int nb_object
    boolean verified
    timestamp upload_date 
  }
inference{
    uuid id PK
    json inference 
    uuid picture_id FK
    uuid user_id FK
    timestamp upload_date
  }
  picture_seed{
    uuid id PK
    uuid picture_id FK
    uuid seed_id FK
    timestamp upload_date
  }
  picture_set ||--o{picture: contains
  picture ||--o{picture: cropped
  picture |o--o{picture_seed: has
  picture_seed }o--o| seed: has
  inference ||--o{ object: detects
  object ||--o{ seed_object: is
  seed_object }o--|| seed: is
  inference ||--|| picture: infers

```

From the Nachet Interactive application, a user can create and delete folders,
so the blob storage and the database must be correctly updated.

When a folder is created, it takes on a name and is created as a `picture_set`
in the database and as a folder in the blob storage container of the user.

There are more issues when the user wants to delete a folder. If the folder
contains validated pictures, it may be useful for training purpose, because it
means there is a valid inference associated with each seed on the picture. The
same applies to pictures imported in batches, which have been downloaded for
training purposes. Our solution is to request confirmation from the user, who
can decide to delete pictures from his container but let us save them, or he can
delete everything anyway, for example if there has been a missed click.

## Prerequisites

- The user must be signed in and have an Azure Storage Container
- The backend needs a connection to the datastore

## Sequence Diagram

### Delete Use Case

```mermaid
sequenceDiagram
    participant User
    participant FE
    participant BE
    participant DS

    User->>FE: Delete Folder
    rect rgb(200, 50, 50)
      FE->>BE: /delete-request
    end
    rect rgb(200, 50, 50)
          BE->>DS: Check if there are validated inferences or pictures from a batch import
note left of DS: Check for picture_seed entities linked to picture id<br> since a verified inference and a batch upload has those
    end
    alt picture_seed exist
        DS-->>BE: Validated inference status or pictures from batch import
        BE->>FE: True : Request user confirmation
        rect rgb(200, 50, 50)
            FE->>User: Ask to keep data for training
note left of FE : "Some of those pictures were validated or upload via the batch import.<br>Do you want us to keep them for training ? <br>If yes, your folder will be deleted but we'll keep the validated pictures.<br>If no, everything will be deleted and unrecoverable.
        end
        alt No
            User ->>FE: delete all
            rect rgb(200, 50, 50)
                FE-->BE:  /delete-permanently
            end
            BE->>DS: delete picture_set
        else YES
            User ->>FE: Keep them
            rect rgb(200, 50, 50)
                FE-->BE: /delete-with-archive
            end
            rect rgb(200, 50, 50)
                BE->>DS: archive data for validated inferences and batch import in picture_set
                    note left of DS: "Pictures are moved in different container <br> DB entities updated" 
                BE->>DS: delete picture_set
                   note left of DS: "Folder and all the files left are deleted, <br>related pictures, inference are deleted." 
            end
       else CANCEL
            User ->>FE: cancel : nothing happens
       end
    else no picture_seed exist
        DS-->>BE: No pictures with validated inference status or from batch import
        BE-->>FE: False: confirmation to delete the folder
        rect rgb(200, 50, 50)
            FE->>User: Ask confirmation
note left of FE : "Are you sure ? Everything in this folder will be deleted and unrecoverable"
        end
        alt Yes
            User ->>FE: delete all
            rect rgb(200, 50, 50)
                FE-->BE:  /delete-permanently
            end
            BE->>DS: delete picture_set
        else CANCEL
            User ->>FE: cancel : nothing happens
        
        end
    end

```

## API Routes

### /create-dir

The `create-dir` route needs a `folder_name` and creates the folder in the
database and in Azure blob storage.

### /get-directories

The `get-directories` route retreives all user directories from the database
with their pictures as a JSON. There are 4 different cases for the pictures :

| **is_verified \\ inference_exist** | **false**              | **true**             |
|------------------------------------|----------------------|-----------------------|
| **false**                           | *should not happend* | inference not verified  |
| **true**                          | batch import | inference verified |

```json
{
"folders" : [
        {
            "picture_set_id" : "xxxx-xxxx-xxxx-xxxx",
            "folder_name" : "folder name",
            "nb_pictures": 4,
            "pictures" : [
                {
                    "picture_id" : "xxxx-xxxx-xxxx-xxxx",
                    "inference_exist": false,
                    "is_validated": true
                },
                ...
            ]
        },
        ...
    ]
}
```

### /get-picture

The `get-picture` route retreives the selected picture as a JSON :

```json
{
    "picture_id" : "xxxx-xxxx-xxxx-xxxx",
    "inference": {
     }
    "image": "data:image/...;base64,xxxxxxxx"
}
```

### /delete-request

The `delete-request` route returns True if there are validated pictures in the
given folder or else returns False.

### /delete-permanently

The `delete-permanently`route deletes the given folder, meaning it deletes the
`picture_set` and everything related in the database, as well as all blobs in
the Azure blob storage.

### /delete-with-archive

The `delete-with-archive` route deletes the given folder from the user container
but moves everything in the dev container.

---

## Gérer les Dossiers

## Table des matières

- [Sommaire](#sommaire)
- [Prérequis](#prérequis)
- [Diagramme de Séquence](#diagramme-de-séquence)
  - [Cas d'Utilisation : Suppression](#cas-dutilisation--suppression)
- [API](#api)
  - [Route /create-dir](#route-create-dir)
  - [Route /get-directories](#route-get-directories)
  - [Route /get-picture](#route-get-picture)
  - [Route /delete-request](#route-delete-request)
  - [Route /delete-permanently](#route-delete-permanently)
  - [Route /delete-with-archive](#route-delete-with-archive)

## Sommaire

Un utilisateur peut obtenir un aperçu de son conteneur de stockage blob dans
l'application Nachet. Il peut posséder plusieurs dossiers dans son conteneur
ainsi que des images. Étant donné que nous utilisons une base de données, ces
dossiers sont liés à la table `picture_set`, et chaque image est également
enregistrée dans la base de données. Voici son schéma actuel:

```mermaid
---
title: Extrait de la structure de la base de données Nachet
---
erDiagram
  picture_set{
    uuid id PK
    json picture_set
    uuid owner_id FK
    timestamp upload_date
  }
  picture{
    uuid id PK
    json picture
    uuid picture_set_id FK
    uuid parent FK
    int nb_object
    boolean verified
    timestamp upload_date 
  }
  inference{
    uuid id PK
    json inference 
    uuid picture_id FK
    uuid user_id FK
    timestamp upload_date
  }
  picture_seed{
    uuid id PK
    uuid picture_id FK
    uuid seed_id FK
    timestamp upload_date
  }
  picture_set ||--o{picture: contient
  picture ||--o{picture: recadré
  picture |o--o{picture_seed: possède
  picture_seed }o--o| seed: contient
  inference ||--o{ object: détecte
  object ||--o{ seed_object: est
  seed_object }o--|| seed: est
  inference ||--|| picture: déduit
```

Depuis l'application Nachet Interactive, un utilisateur peut créer et supprimer
des dossiers, ce qui nécessite une mise à jour correcte du stockage blob et de
la base de données.

Lorsqu'un dossier est créé, il reçoit un nom et est enregistré en tant que
`picture_set` dans la base de données et comme dossier dans le conteneur de
stockage blob de l'utilisateur.

La suppression de dossiers pose plus de défis. Si le dossier contient des images
validées, celles-ci peuvent être utiles pour l'entraînement, car elles sont
associées à une inférence valide pour chaque graine présente sur l'image. Il en
va de même pour les images importées en lots, qui ont été téléchargées à des
fins d'entraînement. Notre solution consiste à demander une confirmation à
l'utilisateur, qui peut choisir de supprimer les images de son conteneur tout en
nous permettant de les conserver, ou de tout supprimer en cas de clic
accidentel, par exemple.

## Prérequis

- L'utilisateur doit être connecté et disposer d'un conteneur Azure Storage.
- Le backend doit être connecté au datastore.

## Diagramme de Séquence

### Cas d'Utilisation : Suppression

```mermaid
sequenceDiagram
    participant Utilisateur
    participant Frontend (FE)
    participant Backend (BE)
    participant Datastore (DS)

    Utilisateur->>FE: Supprimer un dossier
    rect rgb(200, 50, 50)
      FE->>BE: /delete-request
    end
    rect rgb(200, 50, 50)
          BE->>DS: Vérifie s'il existe des inférences validées ou des images issues d'une importation en lot
note left of DS: Vérifie les entités `picture_seed` liées à l'ID de l'image<br> car une inférence validée et une importation en lot en possèdent.
    end
    alt `picture_seed` existe
        DS-->>BE: Statut d'inférence validée ou images issues d'importation en lot
        BE->>FE: True : Demande confirmation de l'utilisateur
        rect rgb(200, 50, 50)
            FE->>Utilisateur: Demande de conserver les données pour l'entraînement
note left of FE : "Certaines de ces images ont été validées ou importées via un lot.<br>Voulez-vous que nous les conservions pour l'entraînement ?<br>Si oui, votre dossier sera supprimé mais nous garderons les images validées.<br>Si non, tout sera supprimé de façon irréversible."
        end
        alt Non
            Utilisateur ->>FE: Supprimer tout
            rect rgb(200, 50, 50)
                FE-->BE: /delete-permanently
            end
            BE->>DS: Supprimer `picture_set`
        else Oui
            Utilisateur ->>FE: Conserver
            rect rgb(200, 50, 50)
                FE-->BE: /delete-with-archive
            end
            rect rgb(200, 50, 50)
                BE->>DS: Archiver les données pour les inférences validées et importations en lot dans `picture_set`
                    note left of DS: "Les images sont déplacées dans un autre conteneur <br> Les entités BD sont mises à jour."
                BE->>DS: Supprimer `picture_set`
                   note left of DS: "Le dossier et tous les fichiers restants sont supprimés,<br> les images et inférences associées sont supprimées." 
            end
       else ANNULER
            Utilisateur ->>FE: Annuler : aucune action
       end
    else `picture_seed` n'existe pas
        DS-->>BE: Pas d'images avec inférences validées ou issues d'importations en lot
        BE-->>FE: Faux : confirmation pour supprimer le dossier
        rect rgb(200, 50, 50)
            FE->>Utilisateur: Demande de confirmation
note left of FE : "Êtes-vous sûr ? Tout dans ce dossier sera supprimé de façon irréversible."
        end
        alt Oui
            Utilisateur ->>FE: Supprimer tout
            rect rgb(200, 50, 50)
                FE-->BE: /delete-permanently
            end
            BE->>DS: Supprimer `picture_set`
        else ANNULER
            Utilisateur ->>FE: Annuler : aucune action
        
        end
    end
```

## API

### Route /create-dir

`create-dir` nécessite un `folder_name` et crée le dossier dans la base
de données ainsi que dans le stockage blob d'Azure.

### Route /get-directories

`get-directories` récupère tous les répertoires de l'utilisateur depuis
la base de données avec leurs images au format JSON. Il existe 4 cas différents
pour les images :

| **is_verified \\ inference_exist** | **false**              | **true**               |
|------------------------------------|------------------------|-------------------------|
| **false**                          | *ne devrait pas arriver* | inférence non vérifiée |
| **true**                           | importation en lot     | inférence vérifiée      |

```json
{
  "folders": [
    {
      "picture_set_id": "xxxx-xxxx-xxxx-xxxx",
      "folder_name": "nom du dossier",
      "nb_pictures": 4,
      "pictures": [
        {
          "picture_id": "xxxx-xxxx-xxxx-xxxx",
          "inference_exist": false,
          "is_validated": true
        },
        ...
      ]
    },
    ...
  ]
}
```

### Route /get-picture

`get-picture` récupère l'image sélectionnée en format JSON :

```json
{
  "picture_id": "xxxx-xxxx-xxxx-xxxx",
  "inference": {},
  "image": "data:image/...;base64,xxxxxxxx"
}
```

### Route /delete-request

`delete-request` renvoie `True` s'il y a des images validées dans le
dossier donné, ou `False` sinon.

### Route /delete-permanently

`delete-permanently` supprime le dossier spécifié, ce qui inclut la
suppression du `picture_set` et de tous les éléments associés dans la base de
données, ainsi que la suppression de tous les blobs dans le stockage blob
d'Azure.

### Route /delete-with-archive

`delete-with-archive` supprime le dossier donné du conteneur
utilisateur, mais déplace tout son contenu vers le conteneur de développement.

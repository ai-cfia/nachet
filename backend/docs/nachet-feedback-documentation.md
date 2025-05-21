# Inference Feedback

([*Le français est disponible au bas de la page*](#rétroaction-sur-linférence))

## Table of Contents

- [Executive Summary](#executive-summary)
- [Prerequisites](#prerequisites)
- [Solution](#solution)
- [Sequence Diagram](#sequence-diagram)
- [API Routes](#api-routes)
  - [/get-user-id](#get-user-id)
  - [/seeds](#seeds)
  - [/feedback-positive](#feedback-positive)
  - [/feedback-negative](#feedback-negative)

## Executive Summary

When seed analysts use Nachet, they should be able to give their feedback on the
result. A pipeline of action needs to be integrated from the Frontend to the
database to be able to register the user feedback. The possible feedback types
are:

- A perfect feedback (Doesn't change anything and validates the inference)
- A new guess is given by the analyst
- The box coordinates have changed
- The box is deleted (not a seed)
- A new box is added

## Prerequisites

- The user must be signed in and have an Azure Storage Container
- The backend needs to have a connection to the datastore
- The user can do an inference request

## Solution

The analyst selects the box for which he or she wishes to give feedback, and
then fills in a form containing information about its correction.
The frontend adapts this information and sends it to the backend, then,
according to each case of feedback, the datastore updates the inference and the
object.

## Sequence Diagram

``` mermaid

sequenceDiagram;
  actor User
  participant Frontend
  participant Backend
  participant Datastore
  participant Database
  

    User ->> Frontend: Validate inference
    alt Perfect Inference
    Frontend -) Backend: Inference result positive (user_id, boxes)
    Backend -) Datastore: new_perfect_inference_feeback(inference_id, user_id, boxes_id)
    Note over Backend, Datastore : Each box_id is an inference object in db
        alt if inference not already verified
            Datastore ->> Database: Set each object.valid = True & object.verified_id=object.top_id
        end
    else Annotated Inference
    Frontend -) Backend: Inference feedback (inference_feedback.json,user_id,inference_id)
    Backend ->> Datastore: Inference feedback (inference_feedback.json, user_id, inference_id)
    Datastore -> Database: Get Inference_result(inference_id)
        loop each Boxes
            alt box has an id value
                alt inference_feedback.box.verified= False
                    Datastore --> Datastore: Next box & flag_all_box_verified=False
                else
                    Datastore -) Database: Set object.verified=True & object.verified_by=user_id
                    Datastore -) Datastore: Compare label & box coordinates
                    alt label value empty
                        Datastore -) Database: Set object.top_inference=Null
                        Datastore -) Database: Set object.modified=False                   
                    else label or box coordinates are changed & not empty
                        Datastore -) Database: Update object.top_inference & object.box_metadata
                        Note over Datastore,Database: if the top label is not part of the seed_object guesses, <br>we will need to create a new instance of seed_object.
                        Datastore -) Database: Set object.modified=true
                    else label and box haven't changed
                        Datastore -) Database: Set object.modified=False
                    end
                end
            else box has no id value
                Datastore -) Database: Create new object and seed_object
            end
        end
    end
    Datastore -) Datastore : verify_inference_status(inference_id, user_id)
    Note over Datastore, Database : set inference verified if all objects have a verified_id

```

## API Routes

### /get-user-id

The `/get-user-id` route retrieves the user-id for a given email.

### /seeds

The `/seeds` route retrieves all the seed names needed for the frontend to build
the form to upload the pictures to the database.

### /feedback-positive

The `/feedback-positive` route is the endpoint that the frontend calls to add a
positive feedback to an inference, giving the inference and the box to validate.

### /feedback-negative

The `/feedback-negative` route is the endpoint that sends the information to the
datastore for a correction feedback to be added to a given inference and box.

---

## Rétroaction sur l'Inférence

## Table des matières

- [Sommaire](#sommaire)
- [Prérequis](#prérequis)
- [La Solution](#la-solution)
- [Diagramme de Séquence](#diagramme-de-séquence)
- [API](#api)
  - [Route /get-user-id](#route-get-user-id)
  - [Route /seeds](#route-seeds)
  - [Route /feedback-positive](#route-feedback-positive)
  - [Route /feedback-negative](#route-feedback-negative)

## Sommaire

Lorsque les analystes de semences utilisent Nachet, ils doivent pouvoir donner
une rétroaction sur le résultat. Une chaîne d'actions doit être intégrée du
Frontend à la base de données pour enregistrer les retours des utilisateurs. Les
types de retours possibles sont :

- Un retour parfait (ne modifie rien et valide l'inférence)
- Une nouvelle hypothèse donnée par l'analyste
- Les coordonnées de la boîte ont changé
- La boîte est supprimée (pas une graine)
- Une nouvelle boîte est ajoutée

## Prérequis

- L'utilisateur doit être connecté et disposer d'un conteneur de stockage Azure
- Le backend doit être connecté au Datastore
- L'utilisateur doit pouvoir effectuer une demande d'inférence

## La Solution

L'analyste sélectionne la boîte pour laquelle il ou elle souhaite donner un
retour, puis remplit un formulaire contenant une série d'informations sur sa
correction. Le frontend adapte ces informations et les envoie au backend. Selon
chaque cas de retour, le datastore met à jour l'inférence et l'objet associé.

## Diagramme de Séquence

```mermaid
sequenceDiagram;
  actor Utilisateur
  participant Frontend
  participant Backend
  participant Datastore
  participant BaseDeDonnées
  

    Utilisateur ->> Frontend: Valider l'inférence
    alt Inférence parfaite
    Frontend -) Backend: Résultat d'inférence positif (user_id, boxes)
    Backend -) Datastore: new_perfect_inference_feedback(inference_id, user_id, boxes_id)
    Note over Backend, Datastore : Chaque box_id est un objet d'inférence dans la base de données
        alt si l'inférence n'est pas encore vérifiée
            Datastore ->> BaseDeDonnées: Définit object.valid=True & object.verified_id=object.top_id
        end
    else Inférence annotée
    Frontend -) Backend: Retour sur l'inférence (inference_feedback.json, user_id, inference_id)
    Backend ->> Datastore: Retour sur l'inférence (inference_feedback.json, user_id, inference_id)
    Datastore -> BaseDeDonnées: Obtenir inference_result(inference_id)
        loop Chaque boîte
            alt La boîte a une valeur d'id
                alt inference_feedback.box.verified= False
                    Datastore --> Datastore: Passe à la boîte suivante & flag_all_box_verified=False
                else
                    Datastore -) BaseDeDonnées: Définit object.verified=True & object.verified_by=user_id
                    Datastore -) Datastore: Compare l'étiquette et les coordonnées de la boîte
                    alt Valeur de l'étiquette vide
                        Datastore -) BaseDeDonnées: Définit object.top_inference=Null
                        Datastore -) BaseDeDonnées: Définit object.modified=False                   
                    else l'étiquette ou les coordonnées de la boîte ont changé et ne sont pas vides
                        Datastore -) BaseDeDonnées: Met à jour object.top_inference & object.box_metadata
                        Note over Datastore,BaseDeDonnées: si l'étiquette principale ne fait pas partie des hypothèses de seed_object, <br>une nouvelle instance de seed_object doit être créée.
                        Datastore -) BaseDeDonnées: Définit object.modified=true
                    else L'étiquette et la boîte n'ont pas changé
                        Datastore -) BaseDeDonnées: Définit object.modified=False
                    end
                end
            else La boîte n'a pas de valeur d'id
                Datastore -) BaseDeDonnées: Crée un nouvel objet et seed_object
            end
        end
    end
    Datastore -) Datastore : verify_inference_status(inference_id, user_id)
    Note over Datastore, BaseDeDonnées : Définit l'inférence comme vérifiée si tous les objets ont un verified_id
```

## API

### Route /get-user-id

`/get-user-id` récupère l'ID utilisateur pour un e-mail donné.

### Route /seeds

`/seeds` permet d'obtenir tous les noms de graines nécessaires pour que
le frontend puisse créer le formulaire d'envoi des images vers la base de
données.

### Route /feedback-positive

`/feedback-positive` est le point d'entrée que le frontend appelle pour
ajouter un retour positif à une inférence, en spécifiant l'inférence et la boîte
à valider.

### Route /feedback-negative

`/feedback-negative` est le point d'entrée qui envoie les informations
au datastore pour qu'un retour correctif soit ajouté à une inférence et une
boîte spécifiques.

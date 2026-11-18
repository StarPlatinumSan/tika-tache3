# Tâche 3 : Analyse de vulnérabilités avec Semgrep et intégration GitHub Actions

**Binôme :** BITULEANU Andrei, LITRE Paul
**Cours :** IFT3913
**Date :** 17/11/26

---

## 1. Environnement et outils

| Élément | Valeur |
|---|---|
| Projet analysé | Apache Tika |
| Module principalement étudié | `tika-core` |
| Outil d'analyse statique | Semgrep OSS 1.185.0 |
| Configuration Semgrep | `p/ci` et `p/java` |
| Nombre de règles utilisées | 188 |
| Intégration continue | GitHub Actions |
| Système de construction | Maven |
| Version Java du workflow existant | JDK 17 |

L'objectif de cette tâche est d'intégrer Semgrep au dépôt GitHub afin de détecter les nouvelles alertes de sécurité lors des modifications du code. Nous devons également comparer les résultats avant et après l'intégration, étudier différents types de vulnérabilités et créer une action GitHub réutilisable.

## 2. Choix du périmètre d'analyse

Nous avons décidé de continuer avec le module `tika-core`, puisque nous l'avions déjà utilisé lors de la tâche 2.

Nous avions initialement considéré quatre fichiers:

| Classe | Raison du choix | Alertes initiales |
|---|---|---|
| `MediaType.java` | Classe avec des tests existants et un comportement relativement simple | 0 |
| `MediaTypeTest.java` | Tests associés à MediaType | 0 |
| `Metadata.java` | Classe déjà étudiée à la tâche 2 | 0 |
| `AbstractMultipleParser.java` | Classe déjà étudiée à la tâche 2 | 0 |

Le premier scan n'a détecté aucune alerte dans ces fichiers avec les règles utilisées. Nous avons donc décidé de conserver `tika-core` comme périmètre principal, mais d'étudier également les autres classes dans lesquelles Semgrep a trouvé des alertes.

## 3. Analyse initiale avec Semgrep

### 3.1 Configuration et procédure

Nous avons commencé par analyser le dépôt avant d'apporter des modifications pour établir un point de comparaison.

**Commit analysé :** `3a60d4c115b6561fa453b8373c7345324ac3fce4`

La configuration utilisée regroupe 188 règles provenant des jeux `p/ci` et `p/java`, après suppression des doublons identiques.

Commande exécutée depuis la racine du dépôt :

```bash
osemgrep scan --experimental \
  --config target/ift3913-semgrep-baseline/rules-p-ci-p-java.yaml \
  --no-rewrite-rule-ids --metrics=off \
  --disable-version-check --no-autofix \
  --verbose --max-log-list-entries=0 \
  --jobs=4 --json .
```

Les résultats ont été enregistrés au format JSON pour permettre une comparaison avec les analyses suivantes.

### 3.2 Résultats du premier scan

| Mesure | Résultat |
|---|---|
| Alertes détectées | 86 |
| Règles ayant produit des alertes | 11 |
| Fichiers concernés | 34 |
| Alertes `WARNING` | 79 |
| Alertes `ERROR` | 6 |
| Alertes `MEDIUM` | 1 |
| Alertes dans `tika-core` | 6 |
| Code de sortie | 0 |

Les trois règles les plus fréquentes concernent les liens HTTP non chiffrés (47 alertes), les actions GitHub utilisant des références modifiables (20 alertes) et les sockets Java sans chiffrement (9 alertes).

Dans `tika-core`, les alertes concernent notamment :

| Fichier | Nombre d'alertes | Problème signalé |
|---|---|---|
| `MimeTypesReader.java` | 1 | Configuration XML et déclarations DOCTYPE |
| `NetworkParser.java` | 1 | Socket sans chiffrement |
| `XMLReaderUtils.java` | 1 | Entités XML externes |
| `testlargerbuffer.html` | 3 | Liens HTTP en clair |

### 3.3 Observations et limites

Le scan a détecté 86 alertes, mais ça ne signifie pas nécessairement que le dépôt contient 86 vulnérabilités exploitables. Semgrep signale des portions de code correspondant à ses règles. Il faut examiner leur contexte pour déterminer si elles représentent un risque réel.

L'analyse a aussi produit 12 avertissements d'analyse partielle concernant 10 fichiers. Ces limites devront être prises en compte lors de la comparaison.

Les résultats du premier scan serviront de référence pour vérifier que notre futur workflow GitHub Actions bloque les nouvelles alertes sans échouer uniquement à cause des alertes déjà présentes.

---

## 4. Intégration de Semgrep dans GitHub Actions

### 4.1 Configuration du workflow

Nous avons modifié le workflow .github/workflows/main-jdk17-build.yml pour effectuer l'analyse de Semgrep avant l'exécution avec Maven. Comme dans l'industrie, le workflow se déclenche automatiquement en faisant un push sur la branche main dans Github Actions et lorsqu'on fait une pull request vers la branche. Dans le cas que Semgrep détecte une nouvelle alerte, le build échoue avant le début des tests.

Nous avons décidé de garder Semgrep OSS 1.185.0 avec les 188 règles du premier scan pour avoir une configuration comparable pour les analyses.

Bien qu'au départ on a essayé de créer un workflow indépendant pour éviter les dégâts, on a fini par opter vers le workflow Maven déjà existant. Ainsi, lorsqu'une nouvelle alerte est détectée le job build échoue dans Actions.

### 4.2 Détection des nouvelles alertes

Le dépot initial contenait 86 alertes après le premier scan avant de débuter comme établi plus haut et on voulait éviter que ces alertes bloquent le nouveau build avant nos modifications.

Nous utilisons donc l'option --baseline-commit de Semgrep. Elle permet de comparer le code actuel avec un commit de référence afin de détecter les nouvelles alertes.

Le script .semgrep/check.py a été développé avec une aide importante de Codex. Nous lui avons demandé d'automatiser cette comparaison et de gérer les différents résultats possibles. Il se reposa sur trois cas:

Code 0 est retourné si aucune nouvelle alerte était détecté, permettant la poursuite du build.
Code 1 roulait lorsqu'une nouvelle alerte était détectée, faisant échouer le build.
Code 2 si une erreur technique entravait une analyse fiable, faisant également échouer le build.

Nous avons choisi de bloquer toutes les nouvelles alertes Semgrep, indépendamment de leur gravité afin d'appliquer un contrôle strict. Le script vérifie également que le commit de référence est valide et que les règles utilisées correspondent à notre configuration initiale. Cela permet d'éviter les comparaisons incorrectes et de rendre les résultats davantage reproductibles.

Pour vérifier le fonctionnement du script, nous avons réalisé plusieurs vérifications local, notamment en conservant une ancienne alerte, en ajoutant une nouvelle alerte et en corrigeant une alerte existante.

Ces vérifications ont permis de confirmer les trois comportements attendus. L'utilisation de Codex a principalement servi à développer et ajuster l'implémentation technique, tandis que les résultats ont été gérés par les rapports et les returns du code.

### 4.3 Problèmes rencontrés lors de la validation

Lors des premières exécutions de GitHub Actions, nous avons rencontré plusieurs problèmes indépendants de Semgrep.

Le premier venait d'Apache RAT, qui refusait certains fichiers de la tâche 2 et nos README à cause de leurs licences. Nous avons donc ajouté des exclusions ciblées dans les fichiers pom.xml, sans désactiver la vérification des licences. Le contrôle RAT a ensuite réussi localement sur les 124 modules Maven.

Le deuxième problème concernait MetadataExtraTest.java. Le test utilisait un constructeur GregorianCalendar qui dépendait de la locale par défaut de la machine. 

Nous avons ajouté Locale.ROOT pour rendre la locale explicite tout en conservant le fuseau UTC. Après cela, les 10 tests de la classe ont réussi et Forbidden APIs n'a détecté aucune violation.

Lors d'une nouvelle exécution GitHub Actions, le build Maven a échoué après environ 40 minutes dans le module tika-pipes-s3-integration-tests. Le rapport Maven indiquait une erreur pendant les tests d'intégration S3.

Ainsi, nous avons identifié le problème venant de l'accès à l'image Docker MinIO utilisé pour les tests. L'erreur HTTP 401 nous a poussé exclure temporairement ce module du build, mais en gardant son code, afin de pouvoir valider Semgrep par tous les moyens nécessaires.

Nous sommes conscients que cette décision réduit la couverture des lignes des tests, mais elle ne change pas la règle de l'analyse Semgrep.

Nous avons alors réalisé que la longue durée des Github Actions était dû au fait que l'on n'avait pas à analyser absolument toute la codebase et qu'isoler simplement tika-core était suffisant pour répondre aux critères de la tâche, rendant la réduction de la couverture des lignes dans le paragraphe plus haut obsolète, car elle respecte les règles.

Cette modification a ensuite permis d'obtenir une exécution réussie sur Github Actions.

### 4.4 Validation sur GitHub


Le dernier résultat confirme le fonctionnement du workflow lorsque aucune nouvelle alerte Semgrep n'est détectée.

Pour vérifier que Semgrep fonctionne correctement, nous avons créé une branche temporaire dans laquelle nous avons ajouté un fichier HTML contenant un lien HTTP non sécurisé.

Nous avons ensuite ouvert une pull request vers main pour voir si GitHub Actions allait détecter ce problème.

Le test a réussi : Semgrep a trouvé la nouvelle alerte et a automatiquement fait échouer le build avec le code 1, avant même que Maven commence ses tests.

Nous avons obtenu le même résultat en local. Cela confirme que notre système bloque les nouvelles alertes et laisse passer celles qui existaient déjà.

Finalement, nous n'avons pas fusionné la pull request pour éviter d'ajouter volontairement ce problème à notre projet. Nous avons également supprimé le pull request pour conserver une clareté dans l'histoire de Github Actions.


## 5. Comparaison des résultats et analyse des vulnérabilités

### 5.1 Comparaison avant-après

### 5.2 Analyse des sept types de vulnérabilités

## 6. Action GitHub réutilisable : Rickroll

### 6.1 Implémentation

### 6.2 Déclenchement sur un échec de test

### 6.3 Résultats de validation

## 7. Conclusion
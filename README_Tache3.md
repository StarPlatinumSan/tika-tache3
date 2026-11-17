# Tâche 3 : Analyse de vulnérabilités avec Semgrep et intégration GitHub Actions

**Binôme :** BITULEANU Andrei, LITRE Paul
**Cours :** IFT3913
**Date :** [Date de remise]

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

*À compléter après l'implémentation du workflow.*

### 4.1 Configuration du workflow

### 4.2 Détection des nouvelles alertes

### 4.3 Validation sur GitHub

## 5. Comparaison des résultats et analyse des vulnérabilités

*À compléter avec les résultats avant-après et l'analyse des sept types demandés.*

### 5.1 Comparaison avant-après

### 5.2 Analyse des sept types de vulnérabilités

## 6. Action GitHub réutilisable : Rickroll

*À compléter après l'implémentation et la validation.*

### 6.1 Implémentation

### 6.2 Déclenchement sur un échec de test

### 6.3 Résultats de validation

## 7. Conclusion

*À rédiger après les vérifications finales.*
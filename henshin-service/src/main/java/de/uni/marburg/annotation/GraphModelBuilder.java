package de.uni.marburg.annotation;

import java.util.HashMap;
import java.util.Map;

import org.eclipse.emf.ecore.EClass;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.EStructuralFeature;

public final class GraphModelBuilder {

    private final EPackage modelPackage;
    private final Map<String, EObject> personas = new HashMap<>();
    private final Map<String, EObject> activities = new HashMap<>();
    private final Map<String, EObject> entities = new HashMap<>();

    public GraphModelBuilder(EPackage modelPackage) {
        this.modelPackage = modelPackage;
    }

    public EObject createGraph() {
        return create("AnnotationGraph");
    }

    @SuppressWarnings("unchecked")
    public EObject addPersona(EObject graph, String name) {
        EObject persona = createNamed("Persona", name);

        var personasFeature
                = graph.eClass().getEStructuralFeature("personas");

        ((java.util.List<EObject>) graph.eGet(personasFeature))
                .add(persona);

        personas.put(name, persona);
        return persona;
    }

    @SuppressWarnings("unchecked")
    public EObject addActivity(EObject graph, String name) {
        EObject activity = createNamed("Activity", name);

        var activitiesFeature
                = graph.eClass().getEStructuralFeature("activities");

        ((java.util.List<EObject>) graph.eGet(activitiesFeature))
                .add(activity);

        activities.put(name, activity);
        return activity;
    }

    @SuppressWarnings("unchecked")
    public EObject addEntity(EObject graph, String name) {
        EObject entity = createNamed("Entity", name);

        var entitiesFeature
                = graph.eClass().getEStructuralFeature("entities");

        ((java.util.List<EObject>) graph.eGet(entitiesFeature))
                .add(entity);

        entities.put(name, entity);
        return entity;
    }

    public void addTrigger(String personaName, String activityName) {
        EObject persona = require(personas, personaName, "Persona");
        EObject activity = require(activities, activityName, "Activity");

        getList(persona, "triggers").add(activity);
    }

    public void addTarget(String activityName, String entityName) {
        EObject activity = require(activities, activityName, "Activity");
        EObject entity = require(entities, entityName, "Entity");

        getList(activity, "targets").add(entity);
    }

    public void addContains(String sourceName, String targetName) {
        EObject source = require(entities, sourceName, "Entity");
        EObject target = require(entities, targetName, "Entity");

        getList(source, "contains").add(target);
    }
    public EObject build(InternalGraph input) {
        EObject graph = createGraph();

        for (String persona : input.nodes().personas()) {
            addPersona(graph, persona);
        }

        for (String activity : input.nodes().activities()) {
            addActivity(graph, activity);
        }

        for (String entity : input.nodes().entities()) {
            addEntity(graph, entity);
        }

        for (InternalGraph.Edge edge : input.edges().triggers()) {
            addTrigger(edge.source(), edge.target());
        }

        for (InternalGraph.Edge edge : input.edges().targets()) {
            addTarget(edge.source(), edge.target());
        }

        for (InternalGraph.Edge edge : input.edges().contains()) {
            addContains(edge.source(), edge.target());
        }

        return graph;
    }

    private EObject createNamed(String className, String name) {
        EObject object = create(className);
        object.eSet(feature(object, "name"), name);
        return object;
    }

    private EObject create(String className) {
        EClass eClass = (EClass) modelPackage.getEClassifier(className);

        if (eClass == null) {
            throw new IllegalArgumentException(
                    "EClass not found: " + className
            );
        }

        return modelPackage.getEFactoryInstance().create(eClass);
    }

    @SuppressWarnings("unchecked")
    private java.util.List<EObject> getList(
            EObject object,
            String featureName
    ) {
        return (java.util.List<EObject>) object.eGet(
                feature(object, featureName)
        );
    }

    private EStructuralFeature feature(
            EObject object,
            String featureName
    ) {
        EStructuralFeature feature
                = object.eClass().getEStructuralFeature(featureName);

        if (feature == null) {
            throw new IllegalArgumentException(
                    "Feature not found: "
                    + object.eClass().getName()
                    + "."
                    + featureName
            );
        }

        return feature;
    }

    private EObject require(
            Map<String, EObject> values,
            String name,
            String type
    ) {
        EObject object = values.get(name);

        if (object == null) {
            throw new IllegalArgumentException(
                    type + " not found: " + name
            );
        }

        return object;
    }
}

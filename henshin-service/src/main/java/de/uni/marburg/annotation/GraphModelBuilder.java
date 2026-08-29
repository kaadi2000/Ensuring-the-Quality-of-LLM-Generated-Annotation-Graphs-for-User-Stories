package de.uni.marburg.annotation;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import org.eclipse.emf.ecore.EClass;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.EStructuralFeature;

public final class GraphModelBuilder {

    private final EPackage modelPackage;

    private final Map<String, EObject> personas = new HashMap<>();
    private final Map<String, EObject> actions = new HashMap<>();
    private final Map<String, EObject> entities = new HashMap<>();

    public GraphModelBuilder(EPackage modelPackage) {
        this.modelPackage = modelPackage;
    }

    public EObject createGraph() {
        personas.clear();
        actions.clear();
        entities.clear();

        return create("AnnotationGraph");
    }

    @SuppressWarnings("unchecked")
    public EObject addPersona(EObject graph, String name) {
        EObject persona = createNamed("Persona", name);

        ((java.util.List<EObject>) graph.eGet(feature(graph, "persona"))).add(persona);

        personas.put(name, persona);

        return persona;
    }

    @SuppressWarnings("unchecked")
    public EObject addAction(EObject graph, String name) {
        EObject action = createNamed("Action", name);

        ((java.util.List<EObject>) graph.eGet(feature(graph, "action"))).add(action);
        actions.put(name, action);
        return action;
    }

    public EObject createEntity(String name) {
        EObject entity = createNamed("Entity", name);
        entities.put(name, entity);
        return entity;
    }

    @SuppressWarnings("unchecked")
    public void addRootEntity(EObject graph, EObject entity) {
        ((java.util.List<EObject>) graph.eGet(feature(graph, "entity"))).add(entity);
    }

    public void addTrigger(String personaName,String actionName) {
        EObject persona = require(personas,personaName,"Persona");
        EObject action = require(actions,actionName,"Action");
        getList(persona, "triggers").add(action);
    }

    public void addTarget(String actionName,String entityName) {
        EObject action = require(actions,actionName,"Action");
        EObject entity = require(entities,entityName,"Entity");
        getList(action, "targets").add(entity);
    }

    public void addContains(String sourceName,String targetName) {
        EObject source = require(entities,sourceName,"Entity");

        EObject target = require(entities,targetName,"Entity");

        getList(source, "contains").add(target);
    }

    public EObject build(InternalGraph input) {

        EObject graph = createGraph();

        for (String persona : input.nodes().personas()) {
            addPersona(graph, persona);
        }
        for (String action : input.nodes().activities()) {
            addAction(graph, action);
        }

        for (String entity : input.nodes().entities()) {
            createEntity(entity);
        }

        Set<String> containedEntities = new HashSet<>();

        for (InternalGraph.Edge edge : input.edges().contains()) {
            containedEntities.add(edge.target());
        }

        for (String entityName : input.nodes().entities()) {

            if (!containedEntities.contains(entityName)) {
                EObject entity = require(entities,entityName,"Entity");
                addRootEntity(graph, entity);
            }
        }

        for (InternalGraph.Edge edge : input.edges().triggers()) {
            addTrigger(edge.source(),edge.target());
        }

        for (InternalGraph.Edge edge : input.edges().targets()) {
            addTarget(edge.source(),edge.target());
        }


        for (InternalGraph.Edge edge : input.edges().contains()) {
            addContains(edge.source(),edge.target());
        }

        return graph;
    }

    private EObject createNamed(String className,String name) {
        EObject object = create(className);
        object.eSet(feature(object, "name"),name);
        return object;
    }

    private EObject create(String className) {

        EClass eClass = (EClass) modelPackage.getEClassifier(className);

        if (eClass == null) {
            throw new IllegalArgumentException("EClass not found: " + className);
        }

        return modelPackage.getEFactoryInstance().create(eClass);
    }

    @SuppressWarnings("unchecked")
    private java.util.List<EObject> getList(EObject object,String featureName) {
        return (java.util.List<EObject>) object.eGet(
                feature(object, featureName)
        );
    }

    private EStructuralFeature feature(EObject object,String featureName) {
        EStructuralFeature feature = object.eClass().getEStructuralFeature(featureName);

        if (feature == null) {
            throw new IllegalArgumentException("Feature not found: "+ object.eClass().getName()+ "."+ featureName);
        }

        return feature;
    }

    private EObject require(Map<String, EObject> values,String name,String type
    ) {
        EObject object = values.get(name);

        if (object == null) {
            throw new IllegalArgumentException(type + " not found: " + name);
        }

        return object;
    }
}
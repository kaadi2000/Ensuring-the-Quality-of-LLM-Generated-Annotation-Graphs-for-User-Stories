package de.uni.marburg.annotation;

import org.eclipse.emf.ecore.EClass;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.EReference;
import org.eclipse.emf.henshin.interpreter.EGraph;
import org.eclipse.emf.henshin.interpreter.Engine;
import org.eclipse.emf.henshin.interpreter.Match;
import org.eclipse.emf.henshin.interpreter.impl.EGraphImpl;
import org.eclipse.emf.henshin.interpreter.impl.EngineImpl;
import org.eclipse.emf.henshin.model.Graph;
import org.eclipse.emf.henshin.model.HenshinFactory;
import org.eclipse.emf.henshin.model.Node;
import org.eclipse.emf.henshin.model.Rule;

public final class HenshinValidator {

    private final EPackage modelPackage;
    private final Engine engine;

    public HenshinValidator(EPackage modelPackage) {
        this.modelPackage = modelPackage;
        this.engine = new EngineImpl();
    }

    public int countSelfContainmentViolations(EObject graphRoot) {
        Rule rule = createSelfContainmentRule();
        EGraph hostGraph = new EGraphImpl(graphRoot);

        int count = 0;

        for (Match ignored : engine.findMatches(
                rule,
                hostGraph,
                null
        )) {
            count++;
        }

        return count;
    }

    private Rule createSelfContainmentRule() {
        EClass entityClass
                = (EClass) modelPackage.getEClassifier("Entity");

        if (entityClass == null) {
            throw new IllegalStateException(
                    "Entity class was not found."
            );
        }

        EReference containsReference
                = (EReference) entityClass
                        .getEStructuralFeature("contains");

        if (containsReference == null) {
            throw new IllegalStateException(
                    "Entity.contains reference was not found."
            );
        }

        HenshinFactory factory = HenshinFactory.eINSTANCE;

        Rule rule = factory.createRule("detectSelfContainment");

        Graph lhs = rule.getLhs();
        Graph rhs = rule.getRhs();

        Node lhsEntity = factory.createNode(
                lhs,
                entityClass,
                "entity"
        );

        factory.createEdge(
                lhsEntity,
                lhsEntity,
                containsReference
        );

        Node rhsEntity = factory.createNode(
                rhs,
                entityClass,
                "entity"
        );

        factory.createEdge(
                rhsEntity,
                rhsEntity,
                containsReference
        );

        rule.getMappings().add(
                factory.createMapping(lhsEntity, rhsEntity)
        );

        return rule;
    }
    public void shutdown() {
        engine.shutdown();
    }
}

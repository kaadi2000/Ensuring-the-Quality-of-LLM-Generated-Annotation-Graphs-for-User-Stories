package de.uni.marburg.annotation;

import java.util.Map;

import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.eclipse.emf.ecore.resource.impl.ResourceSetImpl;
import org.eclipse.emf.ecore.xmi.impl.EcoreResourceFactoryImpl;
import org.eclipse.emf.ecore.xmi.impl.XMIResourceFactoryImpl;

public final class App {

    private App() {
    }

    public static void main(String[] args) throws Exception {
        Resource.Factory.Registry.INSTANCE.getExtensionToFactoryMap().put("ecore", new EcoreResourceFactoryImpl());

        Resource.Factory.Registry.INSTANCE.getExtensionToFactoryMap().put("xmi", new XMIResourceFactoryImpl());

        HenshinValidator validator
                = new HenshinValidator();

        EPackage annotationPackage
                = validator.getModelPackage();

        ResourceSet resourceSet
                = new ResourceSetImpl();

        resourceSet.getPackageRegistry().put(
                annotationPackage.getNsURI(),
                annotationPackage
        );

        GraphModelBuilder builder
                = new GraphModelBuilder(annotationPackage);

        JsonGraphLoader loader = new JsonGraphLoader();

        InternalGraph input = loader.load(java.nio.file.Path.of("input", "graph.json"));

        EObject graph = builder.build(input);

        //HenshinValidator validator = new HenshinValidator();
        HenshinValidator.ParseResult result;

        try {
            result = validator.parse(graph);
        } finally {
            validator.shutdown();
        }

        System.out.println("Parse executed: " + result.isParsed());
        System.out.println("Fully parsed: " + result.isFullyParsed());
        System.out.println("Valid: " + result.isValid());

        System.out.println(
                "Remaining: personas="
                + result.getRemainingPersonas()
                + ", actions="
                + result.getRemainingActions()
                + ", entities="
                + result.getRemainingEntities()
        );

        Resource outputResource = resourceSet.createResource(URI.createFileURI("target/annotation-instance.xmi"));

        System.out.println(
                "Personas: "
                + graph.eGet(
                        graph.eClass()
                                .getEStructuralFeature("persona")
                )
        );

        System.out.println(
                "Actions: "
                + graph.eGet(
                        graph.eClass()
                                .getEStructuralFeature("action")
                )
        );

        System.out.println(
                "Entities: "
                + graph.eGet(
                        graph.eClass()
                                .getEStructuralFeature("entity")
                )
        );

        outputResource.getContents().add(graph);
        outputResource.save(Map.of());

        System.out.println("Metamodel loaded successfully.");
        System.out.println("Graph instance created successfully.");
        System.out.println("Graph instance saved successfully.");
        System.out.println("Saved to target/annotation-instance.xmi");
    }
}

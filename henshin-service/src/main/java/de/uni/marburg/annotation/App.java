package de.uni.marburg.annotation;

import java.net.URL;
import java.util.Map;
import java.util.Objects;

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
        Resource.Factory.Registry.INSTANCE
                .getExtensionToFactoryMap()
                .put("ecore", new EcoreResourceFactoryImpl());

        Resource.Factory.Registry.INSTANCE
                .getExtensionToFactoryMap()
                .put("xmi", new XMIResourceFactoryImpl());

        URL metamodelUrl = Objects.requireNonNull(
                App.class.getClassLoader()
                        .getResource("annotation.ecore"),
                "annotation.ecore was not found"
        );

        ResourceSet resourceSet = new ResourceSetImpl();

        Resource metamodelResource = resourceSet.getResource(
                URI.createURI(metamodelUrl.toString()),
                true
        );

        EPackage annotationPackage
                = (EPackage) metamodelResource.getContents().get(0);

        resourceSet.getPackageRegistry().put(
                annotationPackage.getNsURI(),
                annotationPackage
        );

        GraphModelBuilder builder
                = new GraphModelBuilder(annotationPackage);

        JsonGraphLoader loader = new JsonGraphLoader();

        InternalGraph input = loader.load(
                java.nio.file.Path.of("input", "graph.json")
        );

EObject graph = builder.build(input);

        HenshinValidator validator
                = new HenshinValidator(annotationPackage);

        int violations
                = validator.countSelfContainmentViolations(graph);

        System.out.println(
                "Self-containment violations: " + violations
        );

        validator.shutdown();

        Resource outputResource = resourceSet.createResource(
                URI.createFileURI(
                        "target/annotation-instance.xmi"
                )
        );

        System.out.println(
                "Personas: "
                + graph.eGet(graph.eClass().getEStructuralFeature("personas"))
        );

        System.out.println(
                "Activities: "
                + graph.eGet(graph.eClass().getEStructuralFeature("activities"))
        );

        System.out.println(
                "Entities: "
                + graph.eGet(graph.eClass().getEStructuralFeature("entities"))
        );

        outputResource.getContents().add(graph);
        outputResource.save(Map.of());

        System.out.println("Metamodel loaded successfully.");
        System.out.println("Graph instance created successfully.");
        System.out.println(
                "Saved to target/annotation-instance.xmi"
        );
    }
}

package de.uni.marburg.annotation;
import java.net.URL;
import java.util.Collection;
import java.util.Objects;

import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.EStructuralFeature;
import org.eclipse.emf.ecore.EcorePackage;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.xmi.impl.EcoreResourceFactoryImpl;
import org.eclipse.emf.henshin.interpreter.EGraph;
import org.eclipse.emf.henshin.interpreter.Engine;
import org.eclipse.emf.henshin.interpreter.UnitApplication;
import org.eclipse.emf.henshin.interpreter.impl.EGraphImpl;
import org.eclipse.emf.henshin.interpreter.impl.EngineImpl;
import org.eclipse.emf.henshin.interpreter.impl.UnitApplicationImpl;
import org.eclipse.emf.henshin.model.Module;
import org.eclipse.emf.henshin.model.Unit;
import org.eclipse.emf.henshin.model.resource.HenshinResourceSet;

public final class HenshinValidator {

    private final HenshinResourceSet resourceSet;
    private final EPackage modelPackage;
    private final Engine engine;
    private final Module henshinModule;
    private final Unit parseUnit;

    public HenshinValidator() {

        this.resourceSet = new HenshinResourceSet();

        // Register Ecore before loading the .ecore metamodel
        resourceSet.getPackageRegistry().put(
                EcorePackage.eNS_URI,
                EcorePackage.eINSTANCE
        );

        resourceSet
                .getResourceFactoryRegistry()
                .getExtensionToFactoryMap()
                .put(
                        "ecore",
                        new EcoreResourceFactoryImpl()
                );

        this.modelPackage = loadMetamodel();

        resourceSet.getPackageRegistry().put(
                modelPackage.getNsURI(),
                modelPackage
        );

        this.henshinModule = loadHenshinModule();

        this.engine = new EngineImpl();

        this.parseUnit = henshinModule.getUnit("Parse");

        if (parseUnit == null) {
            throw new IllegalStateException(
                    "Henshin unit 'Parse' was not found."
            );
        }
    }

    public EPackage getModelPackage() {
        return modelPackage;
    }

    public ParseResult parse(EObject graphRoot) {

        EGraph graph = new EGraphImpl(graphRoot);

        UnitApplication application
                = new UnitApplicationImpl(
                        engine,
                        graph,
                        parseUnit,
                        null
                );

        boolean executed = application.execute(null);

        int remainingPersonas
                = countFeature(graphRoot, "persona");

        int remainingActions
                = countFeature(graphRoot, "action");

        int remainingEntities
                = countFeature(graphRoot, "entity");

        boolean fullyParsed
                = remainingPersonas == 0
                && remainingActions == 0
                && remainingEntities == 0;

        return new ParseResult(
                executed,
                fullyParsed,
                executed && fullyParsed,
                remainingPersonas,
                remainingActions,
                remainingEntities
        );
    }

    private EPackage loadMetamodel() {

        URL url = Objects.requireNonNull(
                HenshinValidator.class
                        .getClassLoader()
                        .getResource("parsingAnnotationGraphs.ecore"),
                "parsingAnnotationGraphs.ecore was not found"
        );

        Resource resource = resourceSet.getResource(
                URI.createURI(url.toExternalForm()),
                true
        );

        if (resource.getContents().isEmpty()) {
            throw new IllegalStateException(
                    "Metamodel resource is empty."
            );
        }

        return (EPackage) resource.getContents().get(0);
    }

    private Module loadHenshinModule() {

        URL url = Objects.requireNonNull(
                HenshinValidator.class
                        .getClassLoader()
                        .getResource("parsing.henshin"),
                "parsing.henshin was not found"
        );

        Resource resource = resourceSet.getResource(
                URI.createURI(url.toExternalForm()),
                true
        );

        if (resource.getContents().isEmpty()) {
            throw new IllegalStateException(
                    "parsing.henshin contains no Henshin module."
            );
        }

        return (Module) resource.getContents().get(0);
    }

    private int countFeature(
            EObject graphRoot,
            String featureName
    ) {

        EStructuralFeature feature
                = graphRoot.eClass()
                        .getEStructuralFeature(featureName);

        if (feature == null) {
            throw new IllegalStateException(
                    "Feature not found: " + featureName
            );
        }

        Object value = graphRoot.eGet(feature);

        if (value instanceof Collection<?>) {
            return ((Collection<?>) value).size();
        }

        return value == null ? 0 : 1;
    }

    public void shutdown() {
        engine.shutdown();
    }

    public static final class ParseResult {

        private final boolean parsed;
        private final boolean fullyParsed;
        private final boolean valid;

        private final int remainingPersonas;
        private final int remainingActions;
        private final int remainingEntities;

        public ParseResult(
                boolean parsed,
                boolean fullyParsed,
                boolean valid,
                int remainingPersonas,
                int remainingActions,
                int remainingEntities
        ) {
            this.parsed = parsed;
            this.fullyParsed = fullyParsed;
            this.valid = valid;
            this.remainingPersonas = remainingPersonas;
            this.remainingActions = remainingActions;
            this.remainingEntities = remainingEntities;
        }

        public boolean isParsed() {
            return parsed;
        }

        public boolean isFullyParsed() {
            return fullyParsed;
        }

        public boolean isValid() {
            return valid;
        }

        public int getRemainingPersonas() {
            return remainingPersonas;
        }

        public int getRemainingActions() {
            return remainingActions;
        }

        public int getRemainingEntities() {
            return remainingEntities;
        }
    }
}

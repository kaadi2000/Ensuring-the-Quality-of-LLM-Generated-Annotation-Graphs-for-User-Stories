package de.uni.marburg.annotation;

import java.net.URL;
import java.util.Objects;

import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
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

    private final EPackage modelPackage;
    private final Engine engine;
    private final Module henshinModule;
    private final Unit parseUnit;

    public HenshinValidator(EPackage modelPackage) {
        this.modelPackage = modelPackage;
        this.engine = new EngineImpl();

        this.henshinModule = loadHenshinModule();

        this.parseUnit = henshinModule.getUnit("Parse");

        if (parseUnit == null) {
            throw new IllegalStateException("Henshin unit 'Parse' was not found.");
        }
    }

    public boolean parse(EObject graphRoot) {

        EGraph graph = new EGraphImpl(graphRoot);

        UnitApplication application =
                new UnitApplicationImpl(engine,graph,parseUnit,null);

        return application.execute(null);
    }

    private Module loadHenshinModule() {

    URL henshinUrl = Objects.requireNonNull(
            HenshinValidator.class.getClassLoader().getResource("parsing.henshin"),"parsing.henshin was not found");

    HenshinResourceSet resourceSet = new HenshinResourceSet();

    resourceSet.getPackageRegistry().put(
            modelPackage.getNsURI(),
            modelPackage
    );

    org.eclipse.emf.common.util.URI uri =
            org.eclipse.emf.common.util.URI.createURI(
                    henshinUrl.toExternalForm()
            );

    org.eclipse.emf.ecore.resource.Resource resource = resourceSet.getResource(uri, true);

    if (resource.getContents().isEmpty()) {
        throw new IllegalStateException("parsing.henshin contains no Henshin module.");
    }

    return (Module) resource.getContents().get(0);
}

    public void shutdown() {
        engine.shutdown();
    }
}
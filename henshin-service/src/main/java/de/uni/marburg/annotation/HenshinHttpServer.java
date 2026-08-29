package de.uni.marburg.annotation;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.Objects;

import org.eclipse.emf.common.util.URI;
import org.eclipse.emf.ecore.EObject;
import org.eclipse.emf.ecore.EPackage;
import org.eclipse.emf.ecore.EcorePackage;
import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.resource.ResourceSet;
import org.eclipse.emf.ecore.resource.impl.ResourceSetImpl;
import org.eclipse.emf.ecore.xmi.impl.EcoreResourceFactoryImpl;
import org.eclipse.emf.ecore.xmi.impl.XMIResourceFactoryImpl;
import org.eclipse.emf.ecore.xml.namespace.XMLNamespacePackage;
import org.eclipse.emf.ecore.xml.type.XMLTypePackage;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

public final class HenshinHttpServer {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private final EPackage annotationPackage;

    public HenshinHttpServer() {
        this.annotationPackage = loadMetamodel();
    }

    public static void main(String[] args) throws IOException {
        HenshinHttpServer application = new HenshinHttpServer();

        HttpServer server = HttpServer.create(
                new InetSocketAddress(8081),
                0
        );

        server.createContext("/health", application::health);
        server.createContext("/validate", application::validate);
        server.createContext("/export/xmi", application::exportXmi);

        server.setExecutor(null);
        server.start();

        System.out.println(
                "Henshin service running at http://127.0.0.1:8081"
        );
    }

    private void health(HttpExchange exchange) throws IOException {
        if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
            sendJson(
                    exchange,
                    405,
                    Map.of("message", "Method not allowed.")
            );
            return;
        }

        sendJson(
                exchange,
                200,
                Map.of("status", "ok")
        );
    }

    private void validate(HttpExchange exchange) throws IOException {
        if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
            sendJson(
                    exchange,
                    405,
                    Map.of("message", "Method not allowed.")
            );
            return;
        }

        try {
            InternalGraph input = OBJECT_MAPPER.readValue(
                    exchange.getRequestBody(),
                    InternalGraph.class
            );

            GraphModelBuilder builder
                    = new GraphModelBuilder(annotationPackage);

            EObject graph = builder.build(input);

            HenshinValidator validator
                    = new HenshinValidator(annotationPackage);

            boolean parsed;

try {
    parsed = validator.parse(graph);
} finally {
    validator.shutdown();
}

boolean valid = parsed;

            sendJson(
        exchange,
        200,
        Map.of(
                "valid", valid,
                "parsed", parsed
        )
);

        } catch (IllegalArgumentException exception) {
            sendJson(
                    exchange,
                    400,
                    Map.of(
                            "valid", false,
                            "message", exception.getMessage()
                    )
            );

        } catch (Exception exception) {
            exception.printStackTrace();

            sendJson(
                    exchange,
                    500,
                    Map.of(
                            "valid", false,
                            "message", "Henshin validation failed.",
                            "error", exception.getMessage() == null
                            ? exception.getClass().getSimpleName()
                            : exception.getMessage()
                    )
            );
        }
    }

    private void exportXmi(HttpExchange exchange) throws IOException {
        if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
            sendJson(
                    exchange,
                    405,
                    Map.of("message", "Method not allowed.")
            );
            return;
        }

        try {
            System.out.println("XMI 1: request received");
            InternalGraph input = OBJECT_MAPPER.readValue(
                    exchange.getRequestBody(),
                    InternalGraph.class
            );

            System.out.println("XMI 2: JSON parsed");

            GraphModelBuilder builder
                    = new GraphModelBuilder(annotationPackage);

            EObject graph = builder.build(input);
            System.out.println("XMI 3: EMF graph built");

            ResourceSet resourceSet = new ResourceSetImpl();

            resourceSet.getPackageRegistry().put(
                    EcorePackage.eNS_URI,
                    EcorePackage.eINSTANCE
            );

            resourceSet.getPackageRegistry().put(
                    XMLTypePackage.eNS_URI,
                    XMLTypePackage.eINSTANCE
            );

            resourceSet.getPackageRegistry().put(
                    XMLNamespacePackage.eNS_URI,
                    XMLNamespacePackage.eINSTANCE
            );

            resourceSet.getPackageRegistry().put(
                    annotationPackage.getNsURI(),
                    annotationPackage
            );

            // Resource.Factory.Registry.INSTANCE
            //         .getExtensionToFactoryMap()
            //         .put("xmi", new XMIResourceFactoryImpl());
            resourceSet.getResourceFactoryRegistry()
                    .getExtensionToFactoryMap()
                    .put("xmi", new XMIResourceFactoryImpl());

            Resource resource = resourceSet.createResource(
                    URI.createURI("annotation-graph.xmi")
            );
            System.out.println("XMI 4: resource created");

            resource.getContents().add(graph);

            System.out.println("XMI 5: graph added to resource");

            ByteArrayOutputStream outputStream
                    = new ByteArrayOutputStream();

            resource.save(outputStream, Map.of());

            System.out.println("XMI 6: resource saved");

            byte[] body = outputStream.toByteArray();

            System.out.println("XMI 7: sending response, bytes = " + body.length);

            exchange.getResponseHeaders().set(
                    "Content-Type",
                    "application/xml; charset=UTF-8"
            );

            exchange.getResponseHeaders().set(
                    "Content-Disposition",
                    "attachment; filename=\"annotation-graph.xmi\""
            );

            exchange.sendResponseHeaders(200, body.length);

            try (OutputStream output = exchange.getResponseBody()) {
                output.write(body);
            }

        } catch (IllegalArgumentException exception) {
            sendJson(
                    exchange,
                    400,
                    Map.of(
                            "valid", false,
                            "message", exception.getMessage()
                    )
            );

        } catch (Throwable exception) {
            exception.printStackTrace();

            Throwable cause = exception;

            while (cause.getCause() != null) {
                cause = cause.getCause();
            }

            System.err.println("ROOT CAUSE:");
            cause.printStackTrace();

            String message
                    = cause.getMessage() == null
                    ? cause.getClass().getName()
                    : cause.getClass().getName() + ": " + cause.getMessage();

            sendJson(
                    exchange,
                    500,
                    Map.of(
                            "valid", false,
                            "message", "XMI export failed.",
                            "error", message
                    )
            );
        }
    }

    private static EPackage loadMetamodel() {

        Resource.Factory.Registry.INSTANCE
                .getExtensionToFactoryMap()
                .put("ecore", new EcoreResourceFactoryImpl());

        URL metamodelUrl = Objects.requireNonNull(
                HenshinHttpServer.class
                        .getClassLoader()
                        .getResource("parsingAnnotationGraphs.ecore"),
                "parsingAnnotationGraphs.ecore was not found"
        );

        ResourceSet resourceSet = new ResourceSetImpl();

        resourceSet.getPackageRegistry().put(
                EcorePackage.eNS_URI,
                EcorePackage.eINSTANCE
        );

        EPackage.Registry.INSTANCE.put(
                EcorePackage.eNS_URI,
                EcorePackage.eINSTANCE
        );

        EPackage.Registry.INSTANCE.put(
                EcorePackage.eNS_URI,
                EcorePackage.eINSTANCE
        );

        EPackage.Registry.INSTANCE.put(
                XMLTypePackage.eNS_URI,
                XMLTypePackage.eINSTANCE
        );

        EPackage.Registry.INSTANCE.put(
                XMLNamespacePackage.eNS_URI,
                XMLNamespacePackage.eINSTANCE
        );

        Resource resource = resourceSet.getResource(
                URI.createURI(metamodelUrl.toString()),
                true
        );

        EPackage modelPackage
                = (EPackage) resource.getContents().get(0);

        resourceSet.getPackageRegistry().put(
                modelPackage.getNsURI(),
                modelPackage
        );

        return modelPackage;
    }

    private static void sendJson(
            HttpExchange exchange,
            int statusCode,
            Object response
    ) throws IOException {
        byte[] body = OBJECT_MAPPER
                .writeValueAsString(response)
                .getBytes(StandardCharsets.UTF_8);

        exchange.getResponseHeaders().set(
                "Content-Type",
                "application/json; charset=UTF-8"
        );

        exchange.sendResponseHeaders(statusCode, body.length);

        try (OutputStream output = exchange.getResponseBody()) {
            output.write(body);
        }
    }
}

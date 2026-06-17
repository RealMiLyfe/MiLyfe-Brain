// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MiLyfeBrain",
    platforms: [
        .iOS(.v16),
        .macOS(.v13),
        .watchOS(.v9),
        .tvOS(.v16),
    ],
    products: [
        .library(name: "MiLyfeBrain", targets: ["MiLyfeBrain"]),
    ],
    targets: [
        .target(
            name: "MiLyfeBrain",
            path: "Sources/MiLyfeBrain"
        ),
        .testTarget(
            name: "MiLyfeBrainTests",
            dependencies: ["MiLyfeBrain"]
        ),
    ]
)

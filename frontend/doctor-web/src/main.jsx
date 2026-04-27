import { AppRegistry } from "react-native";

import App from "./App.jsx";
import "./styles.css";

AppRegistry.registerComponent("YallaDoctor", () => App);
AppRegistry.runApplication("YallaDoctor", {
  rootTag: document.getElementById("root"),
});

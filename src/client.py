import sys
import socketio

import numpy as np
from tensorflow.keras.models import model_from_json
from sklearn.metrics import accuracy_score

from utils.training import get_data
from utils.model_utils import encode_layer, decode



class Client:
    def __init__(self, address, client, epochs):
        self.client = client
        self.server = address
        self.sio = socketio.Client()
        self.register_handles()

        self.X_train, self.y_train, self.X_test, self.y_test = get_data(self.client, 'mnist', 'non_iid', 'unbalanced')
        self.model = None
        self.epochs = epochs
        print('Class initialization complete')

    def connect(self):
        print(self.server)
        self.sio.connect(url=self.server)

    def register_handles(self):
        self.sio.on("connection_received", self.connection_received)
        self.sio.on("start_training", self.start_training)
        self.sio.on("end_session", self.disconnect)

    def connection_received(self):
        print(f"Server at {self.server} returned success")

    def start_training(self, global_model):
        self.model = model_from_json(global_model["model_architecture"])
        self.model.compile(optimizer='sgd', loss='categorical_crossentropy', metrics=['accuracy'])
        self.model.set_weights(decode(global_model["model_weights"]))
        print("Starting training")
        self.model.fit(self.X_train, self.y_train, epochs=self.epochs, batch_size=10)
        y_pred = self.model.predict(self.X_test)
        print('Accuracy: ', accuracy_score(self.y_test, np.argmax(y_pred, axis=1)))
        self.send_updates()

    def send_updates(self):
        print('Sending updates...')
        model_weights = dict()
        for layer in self.model.layers:
            if layer.trainable_weights:
                model_weights[layer.name] = encode_layer(layer.get_weights())
        print('Emitting fl_update signal')
        self.sio.emit("fl_update", data=model_weights)

    def disconnect(self):
        print('Invoking disconnect (client)')
        self.model.save("lenet_5.h5")
        self.sio.disconnect()
        return

    def end_session(self, data):
        model_weights = decode(data['model_weights'])
        self.model.set_weights(model_weights)
        print('Received end_session signal from server')


if __name__ == "__main__":
    node = Client(address="http://192.168.0.21:5000", client="client" + str(sys.argv[1]), epochs=int(sys.argv[2]))
    node.connect()
    node.disconnect()

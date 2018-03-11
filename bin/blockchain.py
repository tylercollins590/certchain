import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4

from flask import Flask
from flask import jsonify
from flask import request


class Certchain(object):
    def __init__(self):
        self.chain = []
        self.current_certificates = []

        # Create the genesis block
        self.new_block(previous_hash=1, proof=100)

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm:
        - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
        - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def new_block(self, proof, previous_hash=100):
        """
        Create a new Block in the Certchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'certificates': self.current_certificates,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])

        }

        # Reset the current list of transactions
        self.current_certificates = []

        self.chain.append(block)
        return block

    def new_certificate(self, certifier, certifier_name, recipient, certificate_id, certificate_name, expiration_date):
        """
        Creates a new transaction to go into the next mined Block

        :param certifier: <str> Address of the Certifier
        :param certifier_name: <str> Name of the Certifier
        :param recipient: <str> Address of the Recipient
        :param certificate_id: <int> ID of the certificate
        :param certificate_name: <str> Name of the certificate
        :param expiration_date: <date> Expiration date of the certificate
        :return: <int> The index of the Block that will hold this transaction
        """

        self.current_certificates.append({
            'certifier': certifier,
            'certifier_name': certifier_name,
            'recipient': recipient,
            'certificate_id': certificate_id,
            'certificate_name': certificate_name,
            'expiration_date': expiration_date
        })

        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: <dict> Block
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


# Instantiate our node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the CertChain
certchain = Certchain()


@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = certchain.last_block
    last_proof = last_block['proof']
    proof = certchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof
    # certchain.new_certificate(
    #     sender="0",
    #     recipient=node_identifier,
    #     amount=1,
    # )

    # Forge the new Block by adding it to the chain
    previous_hash = certchain.hash(last_block)
    block = certchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_certificate():
    values = request.get_json()
    print(values)
    # Check that the required fields are in the POST'ed data
    required = ['certifier', 'certifier_name', 'recipient', 'certificate_id',
                'certificate_name', 'expiration_date']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = certchain.new_certificate(values['certifier'], values['certifier_name'],
                                      values['recipient'], values['certificate_id'],
                                      values['certificate_name'], values['expiration_date'])

    response = {'message': f'Transaction will be added to the Block {index}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': certchain.chain,
        'length': len(certchain.chain),
    }
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)



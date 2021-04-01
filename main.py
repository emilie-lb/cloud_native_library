import sys
import argparse
import configparser
import logging
import os.path
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient
import mysql.connector
from mysql.connector import errorcode

# for k,v in os.environ.items():
#     print(k,v)
configuration = {
  'host': os.environ['hostlibrary'],
  'user': os.environ['userlibrary'],
  'password': os.environ['passwordlibrary'],
  'database':'library',
  'client_flags': [mysql.connector.ClientFlag.SSL],
  'ssl_ca': os.environ['sslibrary']
}

logging.basicConfig(
    filename="logging_main.log",
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',)


def upload(cible, blobclient):
    """ Charge le fichier texte local dans l’objet Blob en appelant 
        la méthode upload_blob.
    """
    logging.debug("le programme rentre dans la fonction upload")
    with open(cible, "rb") as f:
        logging.info("Upload the blob from a local file")
        blobclient.upload_blob(f)


def livre_existant(cursor):
    cursor.execute("SELECT titre FROM liste_livres;")
    rows = cursor.fetchall()
    liste_rows = []
    for row in rows :
        liste_rows += row
    titre= input("rentrez un titre: ")
    while titre in liste_rows:
        titre= input("Ce titre existe déjà, rentrez un autre titre: ")
    return titre


def nom_fichier(cible):
    chemin_fichier = cible.split("\\")
    return chemin_fichier[-1]


def main(args,config):
    """
    Fait le liens avec le config.ini
    Fait appel aux fonctions (upload/download/ list).
    """
    logging.debug("entrée dans la fonction main")
    nom_fichier(args.cible)
    blobclient=BlobServiceClient(
        f"https://{config['storage']['account']}.blob.core.windows.net",
        config["storage"]["key"],
        logging_enable=False)
    containerclient=blobclient.get_container_client(config["storage"]["container"])

    try:
        conn = mysql.connector.connect(**configuration)
        print("Connection established")
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with the user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
    else:
        cursor = conn.cursor()

    cursor.execute("SELECT * FROM liste_livres;")
    rows = cursor.fetchall()
    for row in rows:
        print("Data row = (%s, %s, %s, %s)" %(str(row[0]), str(row[1]), str(row[2]), str(row[3])))

    if args.action=="upload": 
        logging.debug("args action est égal à upload ")
        #Lié avec le parser = upload
        blobclient=containerclient.get_blob_client(os.path.basename(args.cible))
        #Lié avec le parser = se connecter au blob client et lui envoyer au fichier
        titre = livre_existant(cursor)
        infos= input("rentrez le nom de l'auteur: ")
        nom_du_fichier = nom_fichier(args.cible)
        url_blob= "https://librarystokage2.blob.core.windows.net/conteneur-livres-blob/"+nom_du_fichier
        logging.debug("essaie d'enregistrer les données dans la base")
        cursor.execute("INSERT INTO liste_livres (titre, infos, url_blob) VALUES (%s, %s, %s);", (titre, infos, url_blob))

        logging.debug("le titre et les infos du nouveau livre a bien été enregistré dans la base")
        print("Inserted",cursor.rowcount,"row(s) of data.")
        conn.commit()
        cursor.close()
        conn.close()
        print(" nouveau livre enregistré dans la base!! Youhou!!")
        return upload(args.cible, blobclient)



if __name__=="__main__":
    #Parser pour utiliser dans son terminal, mode d'emplois dans requirement.txt
    parser=argparse.ArgumentParser("Logiciel d'archivage de documents")
    parser.add_argument("-cfg",default="config.ini",help="chemin du fichier de configuration")
    parser.add_argument("-lvl",default="info",help="niveau de log")
    subparsers=parser.add_subparsers(dest="action",help="type d'operation")
    subparsers.required=True
    
    parser_s=subparsers.add_parser("upload")
    parser_s.add_argument("cible",help="fichier à envoyer")


    args=parser.parse_args()

    loglevels={"debug":logging.DEBUG, "info":logging.INFO, "warning":logging.WARNING, "error":logging.ERROR, "critical":logging.CRITICAL}
    print(loglevels[args.lvl.lower()])
    logging.basicConfig(level=loglevels[args.lvl.lower()])

    config=configparser.ConfigParser()
    config.read(args.cfg)

    sys.exit(main(args,config))

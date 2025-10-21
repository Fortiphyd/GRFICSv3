FROM openjdk:11-jdk

ENV SCADA_LTS_VERSION=2.7.8.1 \
    CATALINA_HOME=/usr/local/tomcat \
    MYSQL_ROOT_PASSWORD=root \
    MYSQL_DATABASE=scadalts \
    MYSQL_USER=root \
    MYSQL_PASSWORD=root \
    TOMCAT_USER=tcuser \
    TOMCAT_PASSWORD=tcuser

# Install dependencies
RUN apt-get update && \
    apt-get install -y wget unzip supervisor mariadb-server libjaxb-api-java libjaxb-java libactivation-java && \
    rm -rf /var/lib/apt/lists/*


# Install Tomcat
RUN wget https://archive.apache.org/dist/tomcat/tomcat-9/v9.0.109/bin/apache-tomcat-9.0.109.tar.gz -O /tmp/tomcat.tar.gz && \
    tar xzf /tmp/tomcat.tar.gz -C /usr/local && \
    mv /usr/local/apache-tomcat-9.0.109 $CATALINA_HOME && \
    rm /tmp/tomcat.tar.gz

# Copy JAXB + activation jars into Tomcat lib
RUN cp /usr/share/java/jaxb-*.jar /usr/local/tomcat/lib/ && \
    cp /usr/share/java/*activation*.jar /usr/local/tomcat/lib/ || true


# Download SCADA-LTS WAR and deploy as ROOT
RUN wget https://github.com/SCADA-LTS/Scada-LTS/releases/download/v${SCADA_LTS_VERSION}/Scada-LTS.war \
         -O $CATALINA_HOME/webapps/ROOT.war && \
    mkdir -p $CATALINA_HOME/webapps/ROOT && \
    cd $CATALINA_HOME/webapps/ROOT && \
    jar -xf ../ROOT.war

# Add MySQL JDBC driver
RUN wget https://dev.mysql.com/get/Downloads/Connector-J/mysql-connector-j-8.3.0.tar.gz -O /tmp/mysql-connector.tar.gz && \
    tar xzf /tmp/mysql-connector.tar.gz -C /tmp && \
    mv /tmp/mysql-connector-j-8.3.0/mysql-connector-j-8.3.0.jar $CATALINA_HOME/lib/ && \
    rm -rf /tmp/mysql-connector*

# Prepare runtime dirs
RUN mkdir -p /var/lib/mysql /run/mysqld /var/log/supervisor && \
    chown -R mysql:mysql /var/lib/mysql /run/mysqld
VOLUME /var/lib/mysql

# Add configs
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY db-init.sh /db-init.sh
RUN chmod +x /db-init.sh


# Add Tomcat JNDI DataSource for SCADA-LTS
RUN sed -i '/<\/Context>/i \
  <Resource name="jdbc/scadalts" auth="Container" \
            type="javax.sql.DataSource" \
            maxTotal="100" maxIdle="30" maxWaitMillis="10000" \
            username="root" password="root" \
            driverClassName="com.mysql.cj.jdbc.Driver" \
            url="jdbc:mysql://localhost:3306/scadalts?serverTimezone=UTC"/>' \
    $CATALINA_HOME/conf/context.xml

# Patch env.properties to use scada:scada direct JDBC
RUN sed -i 's/^db.datasource=true/db.datasource=false/' $CATALINA_HOME/webapps/ROOT/WEB-INF/classes/env.properties && \
    echo "db.url=jdbc:mysql://localhost:3306/scadalts?serverTimezone=UTC" >> $CATALINA_HOME/webapps/ROOT/WEB-INF/classes/env.properties && \
    echo "db.username=scada" >> $CATALINA_HOME/webapps/ROOT/WEB-INF/classes/env.properties && \
    echo "db.password=scada" >> $CATALINA_HOME/webapps/ROOT/WEB-INF/classes/env.properties

COPY 1.png /usr/local/tomcat/static/uploads/1.png
COPY seed_project.sql /seed_project.sql

EXPOSE 8080 3306

CMD ["/usr/bin/supervisord", "-n"]

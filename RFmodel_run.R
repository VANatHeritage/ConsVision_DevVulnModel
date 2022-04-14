# RFmodel_run
# Purpose: Run a random forest development vulnerability model with specified samples
# This includes the following processes:
# - Create new model directory
# - Calculate Variable importance and correlation, remove correlated variables with lower importance
# - Run a 10-fold cross-validation analyze model performance
# - Run a final model for use in model projections, creating partial plots for each variable
#
# Author: David Bucklin
# Created: 2021-10-21

library(sf)
library(randomForest)
library(ROCR)
library(dplyr)
library(SDMTools)
library(lwgeom)
library(ggplot2)
library(readxl)
library(Hmisc)
library(snow)
library(arcgisbinding)
library(dplyr)
arc.check_product()
setwd("D:/git/ConsVision_DevVulnModel")
date <- gsub("-","",Sys.Date())

# Specific name to add to model
sub.nm <- "AllVars" 

# set output model/folder name
proj.mod <- paste0("DevVuln_", sub.nm, "_", date)
proj.o <- paste0("outputs/", proj.mod)
message("Creating project folder ", proj.o, ".")
dir.create(proj.o, showWarnings = F)

# Get full variable table.
file.vartable <- paste0("inputs/vars/vars_DV.xlsx")
vars <- read_excel(file.vartable)
if (sub.nm == "AllVars") {
  vars <- vars %>% filter(use == 1)
} else {
  vars <- read_excel(file.vartable)
  # subset list
  nm <- sub.nm
  vars_subset <- read_excel("inputs/vars/Alternate_Models.xlsx", skip = 1) %>% filter(.data[[nm]] == 'x')
  vars <- vars %>% filter(varname %in% vars_subset$Variable)
}

# training points feature class
training.points <- "TrainingPoints_0616"
d0 <- arc.data2sf(arc.select(arc.open(paste0("inputs/samples/samples.gdb/", training.points))))
d0$class <- d0$DevStatus
plot(d0["class"])
print(table(d0$class))

# Copy and look at grids
d1 <- d0
plot(d1["gridid"])
message(length(unique(d1$gridid)), " unique grids.")

# If not already assigned, give each grid a fold (1:10), making them roughly equal sized (by total samples)
fold.file <- paste0('inputs/samples/', training.points, '_flds_master.txt')
if (file.exists(fold.file)) fld <- read.table(fold.file) else {
  fld <- st_drop_geometry(d1) %>% group_by(gridid) %>% summarise(count = length(gridid)) %>% arrange(desc(count))
  fold <- unlist(lapply(1:((length(unique(d1$gridid)) / 10) + 1), function(x) sample(1:10, 10, F)))
  fld$foldid <- fold[1:nrow(fld)]
  fld %>% group_by(foldid) %>% summarise(count2=sum(count))
  write.table(fld, fold.file)
}

# plot the folds
d1 <- left_join(d1, fld, by = "gridid")
plot(d1["foldid"])

# Check variables
if (all(vars$varname %in% names(d1))) message("All variables found in samples dataset.") else message("Some variables missing from samples dataset.")
ev1 <- names(d1)[names(d1) %in% vars$varname]

# prep data for modeling
d <- st_drop_geometry(d1)[c("class", "sampID", "gridid", "foldid", ev1)]
d <- d[order(d$class),] # sample.fraction relates to order in this column.
rm(d1)
names(d)[1] <- "y"
d$y <- as.factor(d$y)
# NA check
if (!any(unlist(apply(d, 2, FUN = function(x) any(is.na(x)))))) print('Good to go') else print('Some variables have NA values.')

# sample size function, to return amount of samples per class
# NOTE: default behavior for randomForest with replacement would be to use a number equal to the number of samples.
# This function allows to select a number of samples equal to a fraction (frac) of total points in the smaller class (1). Once that
# number is calculated, 'balance' can alter the size of class 1 relative to class 0 (e.g. with balance=0.5, class 1 uses half 
# as may points as class 0).
ssz <- function(d, frac=1, balance=1) {
  ss <- round(min(c(sum(d$y==0), sum(d$y==1))) * frac)
  ss2 <- c(`0`=ss,`1`=round(ss*balance))
  message('Samples per class: 0=', ss2[1], ', 1=', ss2[2])
  return(ss2)
}
# Set Sampling settings here:
repl <- T
frac <- 1
bal <- 1

# Get initial variable importance, variable correlation tree
if (sub.nm == "AllVars") {
  
  rf0.rf <- randomForest(y~., data=d[c("y",ev1)],
                # mtry = 3,
                ntree = 500,
                # sampling scheme
                replace = repl,
                strata = d$y,
                sampsize = ssz(d, frac, bal),  # Just use default sampling to determine variable importance.
                importance = TRUE)
  # Summarize variable importance
  # Decided to use scale=F, see [https://explained.ai/rf-importance/#6.2]: 'Notice that the function does not normalize the 
  # importance values, such as dividing by the standard deviation. According to Conditional variable importance for random forests, 
  # “the raw [permutation] importance… has better statistical properties.”'
  imp <- as.data.frame(importance(rf0.rf, scale = F)) %>% arrange(desc(MeanDecreaseAccuracy)) # as.data.frame(rf0.rf$importance)
  imp$var <- row.names(imp)
  
  # Variable importance
  p <- ggplot(imp) + geom_bar(aes(x=reorder(var, MeanDecreaseAccuracy), y = MeanDecreaseAccuracy), stat = "identity", position = "dodge") +
    theme(axis.text.x = element_text(angle = 90, hjust = 1, vjust = -0.1)) + xlab("Variable") + coord_flip() + 
    ggtitle('Variable importance: initial model')
  p
  ggsave(filename = paste0(proj.o, "/", "initialModel_varImp.png"), p, height = 5, width = 8)
  
  # Variable correlation (Pearson)
  mat <- as.matrix(d[ev1])
  v <- varclus(mat)
  
  # simple correlation-based cutoff into groups 
  cut.corr <- cutree(v$hclust, h = 0.2)  # r2 > 0.8
  length(cut.corr)
  length(table(cut.corr)) # number of groups
  # plot with r2-based group nums
  grpnms <- paste0(as.numeric(cut.corr), ". ", names(cut.corr))
  png(paste0(proj.o, "/", "varCorr_dendrogram.png"), width = 30 * 60, height = 20 * 60, pointsize = 24)
  plot(v, labels = grpnms, lwd=1.5)
  title("Variable groups and dendrogram (correlation >= 0.8 groupings)")
  lines(x = c(0,500), y = c(0.2,0.2), lwd = 1.5, lty = 3, col = "grey50")
  dev.off()
  cut.df <- data.frame(var = names(cut.corr), cor_grp = cut.corr)
  
  # write table
  imp <- left_join(imp, cut.df, 'var')
  write.csv(imp, paste0(proj.o, "/initialModel_varImp.csv"), row.names = F)
  
  # variable reduction
  vars.imp <- left_join(imp, vars %>% dplyr::select(var=varname, group), by = "var") %>% 
    left_join(cut.df) %>% 
    group_by(group, cor_grp) %>%  # UPDATE GROUPS HERE
    slice_max(order_by = MeanDecreaseAccuracy, n=1) %>% filter(MeanDecreaseAccuracy > 0) %>%
    arrange(desc(MeanDecreaseAccuracy))
  vars.imp
  
  # subset variables
  ev <- vars.imp$var
  # if (any(grepl("hwy", ev))) ev <- unique(c(ev, "ttRamps"))  # add ramps variable IF hwy variable selected.
  
} else {
  # Don't run initial process with defined variable selection
  ev <- vars$varname
}
message('Using ', length(ev), ' variables.')
# END variable importance


# Create 'final' model
rf.final <- randomForest(y~., 
                         data = d[c("y",ev)],
                         ntree = 1000,
                         # sampling scheme
                         replace = repl,
                         strata = d$y,
                         sampsize = ssz(d, frac, bal),
                         importance=TRUE)
cm <- rf.final$confusion[,1:2]
rf.final$oob.error <- (cm[1, 2] + cm[2,1]) / sum(cm)

# get OOB predictions for final model
pred <- predict(rf.final, type = 'vote')  # returns OOB predictions. Calculate threshold from this.
d.final <- d["y"]
d.final$predicted <- pred[,2]
rf.final$final.predictions <- d.final

# Final model AUCs based on OOB predictions
p.rocr <- prediction(d.final$predicted, d.final$y)
aucpr <- performance(p.rocr, "aucpr")@y.values[[1]]
print(aucpr)
aucroc <- performance(p.rocr, "auc")@y.values[[1]]
print(aucroc)

# Save variable importance
imp.final <- as.data.frame(importance(rf.final, scale = F)) %>% arrange(desc(MeanDecreaseAccuracy))
imp.final$var <- row.names(imp.final)
write.csv(imp.final, paste0(proj.o, "/finalModel_varImp.csv"), row.names = F)
# Save a plot
imp.final$var <- row.names(imp.final)
imp <- imp.final
p <- ggplot(imp) + geom_bar(aes(x=reorder(var, MeanDecreaseAccuracy), y = MeanDecreaseAccuracy), stat = "identity", position = "dodge") +
  theme(axis.text.x = element_text(angle = 90, hjust = 1, vjust = -0.1)) + xlab("Variable") + coord_flip() +
  ggtitle('Variable importance: final model', subtitle = paste0('Model OOB AUC(PRC): ', round(aucpr, 3)))
p
ggsave(filename = paste0(proj.o, "/", "finalModel_varImp.png"), p, height = 5, width = 8)


### Run k-fold cross-validation
reps <- sort(unique(d$foldid))
df.cv <- data.frame(foldid = reps, nsamp = NA, class0 = NA, class1 = NA,
                    oob.error = NA, roc_auc = NA, prc_auc = NA, 
                    thresh = NA, propCorrect = NA, sens = NA, spec = NA, kappa = NA)
message("Running cross-validation by-grid on cluster...")
ls.gr <- as.list(reps)
cl <- makeCluster(min(parallel::detectCores() - 1, length(ls.gr)), type = "SOCK") 
clusterExport(cl, list("d","df.cv","ev","ssz","frac","bal","repl"), envir = environment()) 
clusterEvalQ(cl, library(randomForest))
clusterEvalQ(cl, library(SDMTools))
clusterEvalQ(cl, library(ROCR))
# Run Cross-validation
cv <- snow::parLapply(cl, x = ls.gr, fun = function(x) {
  
  df0 <- df.cv[df.cv$foldid == x,]
  d.te <- d[d$foldid == x,]  # test set
  d.tr <- d[c("y",ev)][d$foldid != x,]  # train set
  
  df0$nsamp <- nrow(d.te)
  df0$class1 <- sum(d.te$y == 1)
  df0$class0 <- sum(d.te$y == 0)
  
  rf.tr <- randomForest(y~., 
                        data = d.tr,
                        ntree = 1000,
                        replace = repl,
                        strata = d.tr$y,
                        sampsize = ssz(d.tr, frac, bal),
  )
  cm <- rf.tr$confusion[,1:2]
  df0$oob.error <- (cm[1, 2] + cm[2,1]) / sum(cm)
  
  # to get 'votes' for each tree; assumes class `1` is value of interest.
  pred <- as.data.frame(predict(rf.tr, d.te, type="vote"))
  d.te$pred <- pred$`1`
  
  try({
    p.rocr <- prediction(d.te$pred, d.te$y)
    aucpr <- performance(p.rocr, "aucpr")@y.values[[1]]
    df0$prc_auc <- aucpr
    aucroc <- performance(p.rocr, "auc")@y.values[[1]]
    df0$roc_auc <- aucroc
    
    # calculate grid-specific threshold from test data
    # (NOTE: threshold-based statistics were not used in model comparisons)
    ot <- optim.thresh(d.te$y, d.te$pred)
    gt <- ot$`max.sensitivity+specificity`[1]
    df0$thresh <- gt
    res <- confusion.matrix(d.te$y, d.te$pred, gt)
    df0$propCorrect <- prop.correct(res)
    df0$sens <- sensitivity(res)
    df0$spec <- specificity(res)
    df0$kappa <- Kappa(res)
  })
  return(list(df0, d.te[c("sampID", "gridid", "foldid", "y", "pred")]))
})
stopCluster(cl)

# Create results data frames
cv1 <- lapply(cv, function(x) x[1][[1]])
df.cv <- do.call('rbind', cv1)
cv2 <- lapply(cv, function(x) x[2][[1]])
df.cv.full <- do.call('rbind', cv2)

# Get percentiles
df.1 <- data.frame(class = 1, t(quantile(df.cv.full$pred[df.cv.full$y==1], seq(0.05,0.95,0.05))))
df.0 <- data.frame(class = 0, t(quantile(df.cv.full$pred[df.cv.full$y==0], seq(0.05,0.95,0.05))))
df.quant <- rbind(df.1, df.0)
write.csv(df.quant, paste0(proj.o, "/","crossValid_quantiles.csv"), row.names = F)

# Get final threshold from all point predictions
opt.thresh <- optim.thresh(df.cv.full$y, df.cv.full$pred)
thresh <- opt.thresh$`max.sensitivity+specificity`[1]

# CV AUCs
p.rocr <- prediction(df.cv.full$pred, df.cv.full$y)
aucpr <- performance(p.rocr, "aucpr")@y.values[[1]]
print(aucpr)
aucroc <- performance(p.rocr, "auc")@y.values[[1]]
print(aucroc)

# P-R curves
# https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4349800/
# The baseline of PRC is determined by the ratio of positives (P) and negatives (N) as y = P / (P + N)
perf <- performance(p.rocr, "prec", "rec")
png(paste0(proj.o, "/", "crossValid_prCurve.png"), width = 720, height = 720)
plot(perf, colorize=TRUE, ylim=c(0,1), main = paste0('Precision-Recall curve; AUC(PRC) = ', round(aucpr, 3)), cex.main = 1.5, cex.lab=1.2)
baseline <- sum(df.cv.full$y==1) / nrow(df.cv.full)
lines(x=c(0, 1), y = c(baseline, baseline), lty="dashed")
# Fold PR curve(s)
for (i in 1:10) {
  pi <- prediction(df.cv.full$pred[df.cv.full$foldid==i], df.cv.full$y[df.cv.full$foldid==i])
  pip <- performance(pi, "prec", "rec")
  plot(pip, col="grey70", add = T, lwd = 1.5)
}
plot(perf, colorize=TRUE, add = T, lwd = 3)
legend(0.7, 0.99, legend=c("CV folds", "Overall CV"),
       col=c("grey70", "black"), lwd=c(1:5, 3), cex=1.5)
dev.off()

# ROC curves
perf <- performance(p.rocr, "tpr", "fpr")
png(paste0(proj.o, "/", "crossValid_rocCurve.png"), width = 720, height = 720)
plot(perf, colorize=TRUE, ylim = c(0, 1), main = paste0('ROC curve; AUC(ROC) = ', round(aucroc, 3)), cex.main = 1.5, cex.lab=1.2)
# Fold ROC curve(s)
for (i in 1:10) {
  pi <- prediction(df.cv.full$pred[df.cv.full$foldid==i], df.cv.full$y[df.cv.full$foldid==i])
  pip <- performance(pi, "tpr", "fpr")
  plot(pip, col="grey70", add = T, lwd = 1.5)
}
plot(perf, colorize=TRUE, add = T, lwd = 3)
legend(0.7, 0.25, legend=c("CV folds", "Overall CV"),
       col=c("grey70", "black"), lwd=c(1:5, 3), cex=1.5)
dev.off()

# write final stats CSV
cols.keep <- c("foldid", "nsamp", "class0", "class1", "oob.error", "roc_auc", "prc_auc")
res <- confusion.matrix(df.cv.full$y, df.cv.full$pred, thresh)
df.ov <- data.frame(model = proj.mod, type = "cross-validation 06-16",
                    roc_auc = aucroc, prc_auc = aucpr, nsamp = nrow(df.cv.full), class0 = sum(df.cv.full$y==0), class1 = sum(df.cv.full$y==1),
                    thresh = thresh, propCorrect = prop.correct(res), sens = sensitivity(res), spec = specificity(res), kappa = Kappa(res))
# drop threshold-based statistics
write.csv(df.ov[,1:7], file=paste0(proj.o, "/crossValid_stats.csv"), row.names = F)
# write folds stats
write.csv(df.cv[cols.keep], file=paste0(proj.o, "/crossValid_stats_folds.csv"), row.names = F)

# Output CV points to GDB
g2 <- merge(d0["sampID"], df.cv.full, by="sampID")
arc.write(paste0("outputs/samples_validation.gdb/", proj.mod, "_pts"), g2, overwrite=T)

# END Cross-validation


### Create partial plots for final model

# This creates a subset sample of the training data, since pPlots are very slow.
pplotSampN <- min(c(round(nrow(d)/10), 10000)) # take 10% of samples, or 10000, whichever is less
sampprop <- length(d$y[d$y==1])/length(d$y)
pplotSamp <- c(sample((1:length(d$y))[d$y==1], size = ceiling(pplotSampN*sampprop), replace = F),
               sample((1:length(d$y))[d$y==0], size = ceiling(pplotSampN*(1-sampprop)), replace = F))
d.pplot <- d[pplotSamp,ev]

# cluster pPlots
pPlotListLen <- nrow(imp.final)
message("Working on ", pPlotListLen, " partial plots...")
ls.pp <- as.list(imp.final$var)
# Set up cluster
cl <- makeCluster(min(parallel::detectCores() - 1, pPlotListLen), type = "SOCK") 
clusterExport(cl, list("rf.final","d.pplot","ls.pp","vars"), envir = environment()) 
clusterEvalQ(cl, library(randomForest)) 
pPlots <- snow::parLapply(cl, x = ls.pp, fun = function(x) {
  pp <- do.call("partialPlot",
                list(x = rf.final, pred.data = d.pplot, x.var = x, which.class = 1, plot = FALSE))
  pp$varName <- x
  return(pp)
})
stopCluster(cl)

# Save plots
names(pPlots) <- 1:length(pPlots)
par(mfrow = c(2, 1), 
    tcl=-0.2,   #tic length
    cex=1,     #text size
    mgp=c(1.6,0.4,0) #placement of axis title, labels, line
)
ppdir <- paste0(proj.o, "/pPlots")
if (dir.exists(ppdir)) unlink(ppdir, recursive = T, force=T)
dir.create(ppdir)

# Make PNGs for each variable
for (p in 1:length(pPlots)) {
  pl <- pPlots[p][[1]]
  png(file=paste0(ppdir, "/rank", p, "_", pl$varName, '.png'), width=500, height=600)
  
  # density plot
  par(fig=c(0,1,0.6,1), new=TRUE)
  pres.dens <- density(d[d$y == 1, pl$varName])
  abs.dens <- density(d[d$y==0, pl$varName])
  xlim <- c(min(pl$x), quantile(d[,pl$varName][d$y == 1],probs = 0.99)[[1]])
  ylim <- c(0,max(c(abs.dens$y,pres.dens$y)))
  plot(pres.dens, 
       xlim=xlim,  # uses %iles for class-1 values.
       ylim=ylim,
       main=NA,xlab=NA,ylab=NA, axes=FALSE, col="blue", lwd=3)
  lines(abs.dens, col="red", lwd=1.8)
  mtext(paste0(pl$varName), side=3, outer=TRUE, line=-3, cex=1.5)
  
  # p-plot
  par(fig=c(0,1,0,0.8), new=TRUE)
  plot(pl$x, pl$y, xlim = xlim, type = "l", xlab = pl$varName, ylab="log of fraction of votes", lwd=2)
  
  dev.off()
}

# Save Rdata
save(list=ls(), file = paste0(proj.o, "/", proj.mod, ".Rdata"))
rm(list=ls()[!ls() %in% c("proj.mod")])

# Create prediction rasters
source('RFmodel_predict.R')
# 2006
proj06 <- project(proj.mod, year="2006")
proj06.adj <- pred.adjust(proj.mod, year="2006")
# Run validation
indp.validate(proj.mod)

# 2019
proj19 <- project(proj.mod, year="2019")
proj19.adj <- pred.adjust(proj.mod, year="2019")

# end
